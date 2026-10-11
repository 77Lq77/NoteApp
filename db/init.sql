-- NotesApp schema + seed. Loaded automatically by postgres on first start
-- (docker-entrypoint-initdb.d). Runs only when the data volume is empty.

DROP TABLE IF EXISTS notes, enrollments, classes, users CASCADE;

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,          -- stored in clear text (planted flaw #1)
    role       TEXT NOT NULL,          -- 'student' | 'teacher' | 'admin'
    teacher_id INTEGER REFERENCES users(id)
);

CREATE TABLE classes (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    teacher_id INTEGER REFERENCES users(id)
);

CREATE TABLE enrollments (
    id         SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES users(id),
    class_id   INTEGER REFERENCES classes(id)
);

CREATE TABLE notes (
    id         SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES users(id),
    class_id   INTEGER REFERENCES classes(id),
    grade      NUMERIC(4,1),
    comment    TEXT                    -- rendered as rich text / unescaped (planted flaw #10)
);

-- admin (id 1)
INSERT INTO users (username,password,role,teacher_id) VALUES ('admin','admin123','admin',NULL);

-- teachers (ids 2..5)
INSERT INTO users (username,password,role,teacher_id) VALUES ('prof.turing','teach123','teacher',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('prof.lovelace','teach123','teacher',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('prof.hopper','teach123','teacher',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('prof.knuth','teach123','teacher',NULL);

-- students (ids 6..35)
INSERT INTO users (username,password,role,teacher_id) VALUES ('alice','alicepw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('bob','bobpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('carol','carolpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('dave','davepw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('eve','evepw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('frank','frankpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('grace','gracepw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('heidi','heidipw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('ivan','ivanpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('judy','judypw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('mallory','mallorypw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('niaj','niajpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('olivia','oliviapw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('peggy','peggypw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('quentin','quentinpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('rupert','rupertpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('sybil','sybilpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('trent','trentpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('ursula','ursulapw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('victor','victorpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('wendy','wendypw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('xavier','xavierpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('yvonne','yvonnepw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('zack','zackpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('nora','norapw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('liam','liampw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('mia','miapw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('noah','noahpw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('emma','emmapw','student',NULL);
INSERT INTO users (username,password,role,teacher_id) VALUES ('lucas','lucaspw','student',NULL);

-- classes (ids 1..4), teacher_id references users ids 2..5
INSERT INTO classes (name,teacher_id) VALUES ('Mathematics',2);
INSERT INTO classes (name,teacher_id) VALUES ('History',3);
INSERT INTO classes (name,teacher_id) VALUES ('Physics',4);
INSERT INTO classes (name,teacher_id) VALUES ('Computer Science',5);

