
CREATE TABLE ssh_keys (
  id                SERIAL PRIMARY KEY,
  username          CHARACTER VARYING(255) NOT NULL,
  key_name          CHARACTER VARYING(255) NOT NULL,
  ssh_key           TEXT,
  created_at        TIMESTAMP WITH TIME ZONE DEFAULT current_timestamp
);

CREATE INDEX index_ssh_keys_username ON ssh_keys USING btree (username);
