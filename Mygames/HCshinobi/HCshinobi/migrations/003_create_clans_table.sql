-- Create clans table
CREATE TABLE IF NOT EXISTS clans (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    village TEXT,
    population INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rarity TEXT DEFAULT 'Common',
    required_level INTEGER DEFAULT 0,
    required_village TEXT,
    required_strength INTEGER DEFAULT 0,
    required_speed INTEGER DEFAULT 0,
    required_defense INTEGER DEFAULT 0,
    required_chakra INTEGER DEFAULT 0,
    kekkei_genkai TEXT,  -- JSON array of kekkei genkai
    traits TEXT,         -- JSON array of traits
    leader_id INTEGER REFERENCES characters(id)
);

-- Add clan-related columns to characters table
ALTER TABLE characters ADD COLUMN clan TEXT REFERENCES clans(name);
ALTER TABLE characters ADD COLUMN clan_joined_at TIMESTAMP;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_characters_clan ON characters(clan);
CREATE INDEX IF NOT EXISTS idx_clans_village ON clans(village);

-- Insert some default clans
INSERT OR IGNORE INTO clans (name, description, village, rarity, kekkei_genkai, traits) VALUES
('Uchiha', 'A clan known for their powerful Sharingan and exceptional combat abilities.', 'Konohagakure', 'Legendary', '["Sharingan"]', '["Prideful", "Talented", "Fire-natured"]'),
('Hyuga', 'Masters of the Gentle Fist and possessors of the all-seeing Byakugan.', 'Konohagakure', 'Rare', '["Byakugan"]', '["Disciplined", "Perceptive"]'),
('Nara', 'Brilliant strategists who manipulate shadows.', 'Konohagakure', 'Common', '[]', '["Intelligent", "Strategic", "Lazy"]'),
('Akimichi', 'A clan known for their size-manipulation techniques and physical prowess.', 'Konohagakure', 'Common', '[]', '["Strong", "Kind-hearted", "Team-oriented"]'),
('Inuzuka', 'Beast masters who fight alongside their ninken companions.', 'Konohagakure', 'Common', '[]', '["Wild", "Loyal", "Enhanced-senses"]'),
('Aburame', 'Mysterious shinobi who form symbiotic relationships with insects.', 'Konohagakure', 'Common', '[]', '["Logical", "Reserved", "Analytical"]'),
('Uzumaki', 'A clan blessed with powerful life force and exceptional chakra.', 'Uzushiogakure', 'Rare', '[]', '["Determined", "Energetic", "Chakra-rich"]'),
('Senju', 'The clan of a thousand skills, known for their balanced abilities.', 'Konohagakure', 'Legendary', '[]', '["Versatile", "Balanced", "Peace-loving"]'),
('Kaguya', 'A savage clan with the ability to manipulate their own bones.', 'Kirigakure', 'Rare', '["Shikotsumyaku"]', '["Aggressive", "Brutal", "Resilient"]'),
('Yuki', 'A clan gifted with the power to create and manipulate ice.', 'Kirigakure', 'Rare', '["Ice Release"]', '["Calm", "Precise", "Cold-resistant"]'); 