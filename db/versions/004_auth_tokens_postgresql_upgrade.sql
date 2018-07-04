
CREATE TABLE tokens (
  id                SERIAL PRIMARY KEY,
  token_id          CHARACTER VARYING(12) NOT NULL,
  token_hash        CHARACTER VARYING(160) NOT NULL,
  instance_token    BOOL DEFAULT false,
  created_at        TIMESTAMP WITH TIME ZONE DEFAULT current_timestamp,
  last_used         TIMESTAMP WITH TIME ZONE DEFAULT current_timestamp
);

CREATE INDEX index_tokens ON tokens USING btree (token_id);
