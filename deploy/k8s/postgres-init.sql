-- One-off bootstrap: creates the application database and role.
-- Only used when not letting the official Postgres image bootstrap from env vars.
CREATE DATABASE agentdojo;
CREATE USER agentdojo WITH PASSWORD 'agentdojo';
GRANT ALL PRIVILEGES ON DATABASE agentdojo TO agentdojo;
