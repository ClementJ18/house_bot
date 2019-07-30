CREATE TABLE houses.Houses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    initials VARCHAR(5),
    active BOOLEAN NOT NULL DEFAULT 'True',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    role BIGINT,
    description VARCHAR(500),
    channel BIGINT
);

INSERT INTO houses.Houses(name, initials, role, description, channel) 
VALUES ('House of the Racoon', 'HotR', 0, 'The noble house of our King Sebubu', 0),
       ('Bandits', 'B', 0, 'The house of the thieves that have stolen our land', 0);

CREATE TABLE houses.Lands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    owner BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE NOT NULL DEFAULT 2,
    description VARCHAR(500)
);

CREATE TABLE houses.Members (
    id BIGINT PRIMARY KEY,
    house BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE NOT NULL DEFAULT 1,
    noble BOOLEAN NOT NULL DEFAULT 'False'
);

CREATE TABLE houses.Battles (
    id SERIAL PRIMARY KEY,
    attacker BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE,
    defender BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE,
    victor BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    land BIGINT REFERENCES houses.Lands(id) ON DELETE CASCADE,
    aid BOOLEAN NOT NULL DEFAULT 'False'
);

CREATE TABLE houses.Alliances (
    house1 BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE,
    house2 BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE,
    PRIMARY KEY (house1, house2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    broken TIMESTAMPTZ DEFAULT NULL
);

CREATE TYPE rarityCategory AS ENUM ('common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic');
CREATE TYPE conditionStatus AS ENUM ('gift', 'scouting', 'looting');

CREATE TABLE houses.Sets (
    id SERIAL PRIMARY KEY,
    attack DECIMAL(4) NOT NULL DEFAULT 0,
    defense DECIMAL(4) NOT NULL DEFAULT 0,
    prisoner DECIMAL(4) NOT NULL DEFAULT 0,
    land DECIMAL(4) NOT NULL DEFAULT 0,
    capped BOOLEAN NOT NULL DEFAULT 'True'
);

INSERT INTO houses.Sets VALUES;

CREATE TABLE houses.Artefacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    description VARCHAR(500),
    attack DECIMAL(4) NOT NULL DEFAULT 0,
    defense DECIMAL(4) NOT NULL DEFAULT 0,
    prisoner DECIMAL(4) NOT NULL DEFAULT 0,
    land DECIMAL(4) NOT NULL DEFAULT 0,
    owner BIGINT REFERENCES houses.Houses(id) ON DELETE CASCADE NOT NULL DEFAULT 1,
    capped BOOLEAN NOT NULL DEFAULT 'True',
    rarity rarityCategory,
    condition conditionStatus,
    hidden BOOLEAN NOT NULL DEFAULT 'True',
    set_id REFERENCES houses.Sets(id) ON DELETE CASCADE NOT NULL DEFAULT 0
);

CREATE TABLE houses.Landmarks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20),
    description VARCHAR(500),
    attack DECIMAL(4) NOT NULL DEFAULT 0,
    defense DECIMAL(4) NOT NULL DEFAULT 0,
    location BIGINT REFERENCES houses.Lands(id) ON DELETE CASCADE NOT NULL DEFAULT 1,
    capped BOOLEAN NOT NULL DEFAULT 'True',
    hidden BOOLEAN NOT NULL DEFAULT 'True'
);

CREATE TABLE houses.Prisoners (
    id BIGINT PRIMARY KEY REFERENCES houses.Members(id) ON DELETE CASCADE,
    captor BIGINT REFERENCES houses.Houses(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
