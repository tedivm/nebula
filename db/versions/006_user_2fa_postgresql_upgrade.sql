
CREATE TABLE users (
  id                SERIAL PRIMARY KEY,
  username          CHARACTER VARYING(255) UNIQUE NOT NULL,
  security_token    CHARACTER VARYING(32)
);

CREATE INDEX index_users_username ON users USING btree (username);
