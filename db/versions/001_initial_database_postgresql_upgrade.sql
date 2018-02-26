CREATE TABLE profiles (
  id SERIAL PRIMARY KEY,
  name CHARACTER VARYING(255) NOT NULL,
  ami CHARACTER VARYING(255) NOT NULL,
  userdata TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT current_timestamp
);

CREATE INDEX index_profiles_name ON profiles USING btree (name);
CREATE INDEX index_profiles_ami ON profiles USING btree (ami);
