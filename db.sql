CREATE TABLE Houses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    initials VARCHAR(5),
    active BOOLEAN NOT NULL DEFAULT "True",
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    role BIGINT,
    description VARCHAR(500),
    channel BIGINT
)

INSERT INTO HOUSES("name", "initials", "role", "description", "channel") 
VALUES ("House of the Racoon", "HotR", 00000000000, "The noble house of our King Sebubu", 00000000000),
       ("Bandits", "B", 00000000000, "The house of the thieves that have stolen our land", 00000000000)

CREATE TABLE Lands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    owner BIGINT NOT NULL DEFAULT 1 REFERENCES Houses(id),
    description VARCHAR(500)
)

CREATE TABLE Members (
    id BIGINT PRIMARY KEY,
    house BIGINT REFERENCES Houses(id),
    noble BOOLEAN NOT NULL DEFAULT "False"
)

CREATE TABLE Battles (
    id SERIAL PRIMARY KEY,
    attacker BIGINT REFERENCES Houses(id),
    defender BIGINT REFERENCES Houses(id),
    victor BIGINT REFERENCES Houses(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    land BIGINT REFERENCES Lands(id),
    aid BOOLEAN NOT NULL DEFAULT "False"
)

CREATE TABLE Alliance (
    house1 BIGINT REFERENCES Houses(id),
    house2 BIGINT REFERENCES Houses(id),
    PRIMARY KEY (house1, house2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    broken TIMESTAMPTZ DEFAULT NULL
)
