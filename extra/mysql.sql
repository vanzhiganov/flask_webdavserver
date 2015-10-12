CREATE DATABASE webdav;

CREATE TABLE users(
 id INT NOT NULL AUTO_INCREMENT,
 email VARCHAR(100) NOT NULL,
 password VARCHAR(40) NOT NULL,
 PRIMARY KEY(id)
 );


INSERT INTO users (email, password) VALUES ('admin@admin.ru','admin');
