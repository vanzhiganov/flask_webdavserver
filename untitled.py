from functools import wraps
import mimetypes
from time import timezone, strftime, localtime, gmtime
import hashlib
import os
from io import StringIO
import xml.etree.ElementTree as ET
import urllib

from flask import g
from flask import Flask
from flask import request
from flask import Response
from flaskext.mysql import MySQL


# from lib import propfind


mysql = MySQL()
app = Flask(__name__)
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'sqladmin'
app.config['MYSQL_DATABASE_DB'] = 'xstorage'
app.config['MYSQL_DATABASE_HOST'] = '10.10.10.4'
mysql.init_app(app)


methods = [
    'PROPFIND', 'GET', 'HEAD', 'POST', 'DELETE', 'PUT', 'COPY', 'MOVE', 'LOCK', 'UNLOCK'
    'PROPPATCH', 'MKCOL'
]


class Paths:
    struct = {}

    def __init__(self, path='.'):
        for fileitem in os.listdir(path):
            if path != '.':
                fileitem = path + os.sep + fileitem
                # print fileitem
            # if fileitem.endswith('.mp3'):
            #     audio = None
                self.addItem(file, *self.getData(file))
            #     print("{}:{}:{}".format(audio['artist'][0],
            #                             audio['album'][0],
            #                             audio['title'][0]))

    def addItem(self, filename):
        # self.addAlbum(artist, album)
        # if audio not in self.struct[artist][album]:
        self.struct[filename] = filename

    def addArtist(self, artist):
        if artist not in self.struct:
            self.struct[artist] = {}

    def addAlbum(self, artist, album):
        self.addArtist(artist)
        if album not in self.struct[artist]:
            self.struct[artist][album] = {}

    def getFilename(self, artist, album, audio):
        art = self.struct.get(artist)
        if art is None:
            return
        alb = art.get(album)
        if alb is None:
            return
        aud = alb.get(audio)
        return aud

    def getArtists(self):
        return self.struct.keys()

    def getAlbums(self, artist):
        return self.struct.get(artist)

    def getAudios(self, artist, album):
        alb = self.getAlbums(artist)
        if alb is not None:
            return alb.get(album)

    def getBasefile(self, artist=None, album=None):
        if artist is None:
            art = list(self.struct.keys())[0]
            return self.getBasefile(art)
        if album is None:
            out = list(list(self.struct.values())[0].values())[0]
        else:
            out = self.struct[artist][album]
        return list(out.values())[0]

    @staticmethod
    def getData(filename, root=False):
        if not root:
            audio = None
            artist = audio.get('artist', ('noname',))[0]
            if "http" in artist:
                artist = 'noname'
            album = audio.get('album', ('noname',))[0]
            if "http" in album:
                album = 'noname'
            title = audio.get('title', (filename,))[0] + ".mp3"
            if "http" in title:
                title = filename
            return artist, album, title
        elif root:
            return os.sep, '', ''


class File:
    def __init__(self, name, filename, parent):
        self.name = name
        self.basefile = filename
        self.parent = parent

    def getProperties(self):
        st = os.stat(self.basefile)
        properties = {'creationdate': unixdate2iso8601(st.st_ctime),
                      'getlastmodified': unixdate2httpdate(st.st_mtime),
                      'displayname': self.name,
                      'getetag': hashlib.md5(self.name.encode()).hexdigest(),
                      'getcontentlength': st.st_size,
                      'getcontenttype':  mimetypes.guess_type(self.basefile)[0],
                      'getcontentlanguage': None, }
        if self.basefile[0] == ".":
            properties['ishidden'] = 1
        if not os.access(self.basefile, os.W_OK):
            properties['isreadonly'] = 1
        return properties


class DirCollection:
    MIME_TYPE = 'httpd/unix-directory'

    def __init__(self, basefile, type, virtualfs, parent):
        self.basefile = basefile
        self.artist, alb, aud = virtualfs.getData(basefile, type == 'root')
        self.name = self.virtualname = self.artist
        self.parent = parent
        self.virtualfs = virtualfs
        self.type = type

    def getProperties(self):
        st = os.stat(self.basefile)
        properties = {
            'creationdate': unixdate2iso8601(st.st_ctime),
            'getlastmodified': unixdate2httpdate(st.st_mtime),
            'displayname': self.name,
            'getetag': hashlib.md5(self.name.encode()).hexdigest(),
            'resourcetype': '<D:collection/>',
            'iscollection': 1,
            'getcontenttype': self.MIME_TYPE
        }
        if self.virtualname[0] == ".":
            properties['ishidden'] = 1
        if not os.access(self.basefile, os.W_OK):
            properties['isreadonly'] = 1
        if self.parent is None:
            properties['isroot'] = 1
        return properties

    def getMembers(self):
        members = []
        if self.type == 'root':
            for artist in self.virtualfs.getArtists():
                basefile = self.virtualfs.getBasefile(artist)
                members += [DirCollection(basefile,
                                          'artist',
                                          self.virtualfs,
                                          self)]
        elif self.type == 'artist':
            for album in self.virtualfs.getAlbums(self.artist):
                basefile = self.virtualfs.getBasefile(self.artist, album)
                members += [DirCollection(basefile,
                                          'album',
                                          self.virtualfs,
                                          self)]
        elif self.type == "album":
            for audio, filename in self.virtualfs.getAudios(self.artist,
                                                            self.album).items():
                members += [File(audio, filename, self)]
        return members

    def findMember(self, name):
        if name[-1] == '/':
            name = name[:-1]
        if self.type == 'root':
            listmembers = self.virtualfs.getArtists()
        elif self.type == 'artist':
            listmembers = self.virtualfs.getAlbums(self.artist)
        elif self.type == 'album':
            listmembers = self.virtualfs.getAudios(self.artist, self.album)

        if name in listmembers:
            if self.type == 'root':
                return DirCollection(self.virtualfs.getBasefile(),
                                     'artist',
                                     self.virtualfs,
                                     self)
            elif self.type == 'artist':
                return DirCollection(self.virtualfs.getBasefile(self.artist),
                                     'album',
                                     self.virtualfs,
                                     self)
            elif self.type == 'album':
                filename = self.virtualfs.getFilename(self.artist, self.album, name)
                return File(name, filename, self)


def get_absolute_path(path):
    data = split_path(urllib.parse.unquote(path))
    filename = g.VIRTUALFS.getFilename(data[0], data[1], data[2])
    return os.path.join(g.FILE_PATH, filename)


def real_path(path):
    return path


def virt_path(path):
    return path


def unixdate2iso8601(d):
    tz = timezone / 3600
    tz = '%+03d' % tz
    return strftime('%Y-%m-%dT%H:%M:%S', localtime(d)) + tz + ':00'


def unixdate2httpdate(d):
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(d))


def split_path(path):
    # split'/dir1/dir2/file' in ['dir1/', 'dir2/', 'file']
    out = path.split('/')[1:]
    while out and out[-1] in ('', '/'):
        out = out[:-1]
        if len(out) > 0:
            out[-1] += '/'
    return out


def path_elem_prev(path):
    # Returns split path (see split_path())
    # and Member object of the next to last element
    path = split_path(urllib.parse.unquote(path))
    elem = g.ROOT
    for e in path[:-1]:
        elem = elem.findMember(e)
        if elem is None:
            break
    return path, elem

#


def check_auth(username, password):
    """
    This function is called to check if a username /
    password combination is valid.
    """

    email = username
    password = password
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT COUNT(*) FROM dav_users WHERE email='" + email + "' AND password='" + password + "'")
    data = cursor.fetchone()

    if data == 0:
        return False
    else:
        return True
    # return username == 'admin' and password == 'secret'


def authenticate():
    """Sends a 401 response that enables basic auth"""
    response = 'Could not verify your access level for that URL.\n' \
               'You have to login with proper credentials'

    return Response(response, 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        g.username = auth.username
        return f(*args, **kwargs)
    return decorated


@app.route('/', methods=methods)
@requires_auth
def hello_world():
    # propfind.PROPFIND('/', 1)
    FILE_DIR = '/tmp'
    g.FILE_PATH = os.path.join(os.getcwd(), FILE_DIR)
    g.VIRTUALFS = Paths(g.FILE_PATH)
    g.ROOT = DirCollection(g.FILE_PATH, 'root', g.VIRTUALFS, None)

    print dir(g.ROOT)
    # print g.ROOT
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
