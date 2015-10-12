CREATE DATABASE webdav;

CREATE TABLE users (
  id int(11) NOT NULL AUTO_INCREMENT,
  email varchar(128) NOT NULL,
  password varchar(64) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY unique_email (email)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

INSERT INTO users (email, password) VALUES ('admin@admin.ru','admin');
