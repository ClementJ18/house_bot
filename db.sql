CREATE TABLE Houses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    initials VARCHAR(5),
    active BOOLEAN NOT NULL DEFAULT 'True',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    role BIGINT,
    description VARCHAR(500),
    channel BIGINT,
);

INSERT INTO Houses(name, initials, role, description, channel) 
VALUES ('House of the Racoon', 'HotR', 0, 'The noble house of our King Sebubu', 0),
       ('Bandits', 'B', 0, 'The house of the thieves that have stolen our land', 0);

CREATE TABLE Lands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    owner BIGINT NOT NULL DEFAULT 2 REFERENCES Houses(id) ON DELETE CASCADE,
    description VARCHAR(500)
);

CREATE TABLE Members (
    id BIGINT PRIMARY KEY,
    house BIGINT REFERENCES Houses(id) NOT NULL DEFAULT 1 ON DELETE CASCADE,
    noble BOOLEAN NOT NULL DEFAULT 'False'
);

CREATE TABLE Battles (
    id SERIAL PRIMARY KEY,
    attacker BIGINT REFERENCES Houses(id) ON DELETE CASCADE,
    defender BIGINT REFERENCES Houses(id) ON DELETE CASCADE,
    victor BIGINT REFERENCES Houses(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    land BIGINT REFERENCES Lands(id) ON DELETE CASCADE,
    aid BOOLEAN NOT NULL DEFAULT 'False'
);

CREATE TABLE Alliances (
    house1 BIGINT REFERENCES Houses(id) ON DELETE CASCADE,
    house2 BIGINT REFERENCES Houses(id) ON DELETE CASCADE,
    PRIMARY KEY (house1, house2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    broken TIMESTAMPTZ DEFAULT NULL
);

CREATE TABLE Modifiers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    description VARCHAR(500),
    attack DECIMAL(4) NOT NULL DEFAULT 1.00,
    defense DECIMAL(4) NOT NULL DEFAULT 1.00,
    owner BIGINT REFERENCES House(id) NOT NULL DEFAULT 1 ON DELETE CASCADE
    capped BOOLEAN NOT NULL DEFAULT 'True'
);

CREATE TABLE Prisonners (
    id BIGINT PRIMARY KEY REFERENCES Members(id),
    captor BIGINT REFERENCES Houses(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
