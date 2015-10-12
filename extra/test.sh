curl -i -X PROPFIND http://localhost:5000/ --upload-file - -H "Depth: 1" <<end
<?xml version="1.0"?><a:propfind xmlns:a="DAV:"><a:prop><a:resourcetype/></a:prop></a:propfind>
end