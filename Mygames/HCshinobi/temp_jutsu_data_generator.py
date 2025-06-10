import json

master_list = [
    {
        "id": "katon_spark_flicker",
        "name": "Katon: Spark Flicker",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "katon_ember_palm",
        "name": "Katon: Ember Palm",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "katon_smoke_wisp",
        "name": "Katon: Smoke Wisp",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "katon_ember_shuriken",
        "name": "Katon: Ember Shuriken",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "katon_fire_fang",
        "name": "Katon: Fire Fang",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "katon_blister_dash",
        "name": "Katon: Blister Dash",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "katon_burning_feint",
        "name": "Katon: Burning Feint",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "katon_fireball_jutsu",
        "name": "Katon: Fireball Jutsu",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "katon_flame_serpent",
        "name": "Katon: Flame Serpent",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "katon_scorch_barrage",
        "name": "Katon: Scorch Barrage",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "katon_ashen_armor",
        "name": "Katon: Ashen Armor",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "katon_heat_mirage",
        "name": "Katon: Heat Mirage",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "katon_blazing_talon",
        "name": "Katon: Blazing Talon",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "katon_incineration_clones",
        "name": "Katon: Incineration Clones",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "katon_inferno_net",
        "name": "Katon: Inferno Net",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "katon_pillar_of_flame",
        "name": "Katon: Pillar of Flame",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "katon_dragon_s_breath",
        "name": "Katon: Dragon's Breath",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "katon_hellfire_prison",
        "name": "Katon: Hellfire Prison",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "katon_ashen_tempest",
        "name": "Katon: Ashen Tempest",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "katon_black_phoenix_rebirth",
        "name": "Katon: Black Phoenix Rebirth",
        "rank": "S",
        "type": "Ninjutsu",
        "element": "Katon",
        "description": "No description available.",
        "chakra_cost": 150,
        "shop_cost": 15000
    },
    {
        "id": "suiton_moisture_sense",
        "name": "Suiton: Moisture Sense",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "suiton_bubble_veil",
        "name": "Suiton: Bubble Veil",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "suiton_wet_palm",
        "name": "Suiton: Wet Palm",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "suiton_water_needle_shot",
        "name": "Suiton: Water Needle Shot",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "suiton_ripple_step",
        "name": "Suiton: Ripple Step",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "suiton_aqua_lash",
        "name": "Suiton: Aqua Lash",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "suiton_drizzle_cloak",
        "name": "Suiton: Drizzle Cloak",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "suiton_water_bullet_jutsu",
        "name": "Suiton: Water Bullet Jutsu",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "suiton_water_clone_jutsu",
        "name": "Suiton: Water Clone Jutsu",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "suiton_flowing_wall",
        "name": "Suiton: Flowing Wall",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "suiton_torrent_fang",
        "name": "Suiton: Torrent Fang",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "suiton_mist_blade_technique",
        "name": "Suiton: Mist Blade Technique",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "suiton_riptide_crash",
        "name": "Suiton: Riptide Crash",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "suiton_binding_current",
        "name": "Suiton: Binding Current",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "suiton_aqua_pulse_field",
        "name": "Suiton: Aqua Pulse Field",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "suiton_rain_of_sorrow",
        "name": "Suiton: Rain of Sorrow",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "suiton_great_water_dragon",
        "name": "Suiton: Great Water Dragon",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "suiton_abyss_maw",
        "name": "Suiton: Abyss Maw",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "suiton_oceanic_armor",
        "name": "Suiton: Oceanic Armor",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "suiton_leviathan_s_wrath",
        "name": "Suiton: Leviathan's Wrath",
        "rank": "S",
        "type": "Ninjutsu",
        "element": "Suiton",
        "description": "No description available.",
        "chakra_cost": 150,
        "shop_cost": 15000
    },
    {
        "id": "doton_pebble_shot",
        "name": "Doton: Pebble Shot",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "doton_mud_seal",
        "name": "Doton: Mud Seal",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "doton_dust_sight",
        "name": "Doton: Dust Sight",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "doton_stone_fist",
        "name": "Doton: Stone Fist",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "doton_gravel_spit",
        "name": "Doton: Gravel Spit",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "doton_earthen_pads",
        "name": "Doton: Earthen Pads",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "doton_soil_grip",
        "name": "Doton: Soil Grip",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "doton_earth_wall",
        "name": "Doton: Earth Wall",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "doton_rock_clone_jutsu",
        "name": "Doton: Rock Clone Jutsu",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "doton_spire_burst",
        "name": "Doton: Spire Burst",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "doton_ground_pulse",
        "name": "Doton: Ground Pulse",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "doton_earthen_maw",
        "name": "Doton: Earthen Maw",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "doton_armor_of_gaia",
        "name": "Doton: Armor of Gaia",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "doton_shifting_terrain",
        "name": "Doton: Shifting Terrain",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "doton_stone_coffin",
        "name": "Doton: Stone Coffin",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "doton_quake_palm",
        "name": "Doton: Quake Palm",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "doton_earth_dragon_barrage",
        "name": "Doton: Earth Dragon Barrage",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "doton_fortress_technique",
        "name": "Doton: Fortress Technique",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "doton_seismic_rift",
        "name": "Doton: Seismic Rift",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "doton_titan_s_wrath",
        "name": "Doton: Titan's Wrath",
        "rank": "S",
        "type": "Ninjutsu",
        "element": "Doton",
        "description": "No description available.",
        "chakra_cost": 150,
        "shop_cost": 15000
    },
    {
        "id": "raiton_static_touch",
        "name": "Raiton: Static Touch",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "raiton_spark_glimmer",
        "name": "Raiton: Spark Glimmer",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "raiton_hair_stand_technique",
        "name": "Raiton: Hair Stand Technique",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "raiton_shock_darts",
        "name": "Raiton: Shock Darts",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "raiton_conductive_fist",
        "name": "Raiton: Conductive Fist",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "raiton_charge_step",
        "name": "Raiton: Charge Step",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "raiton_pulse_wire",
        "name": "Raiton: Pulse Wire",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "raiton_lightning_clone",
        "name": "Raiton: Lightning Clone",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "raiton_thunder_line",
        "name": "Raiton: Thunder Line",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "raiton_arc_cage",
        "name": "Raiton: Arc Cage",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "raiton_volt_trap",
        "name": "Raiton: Volt Trap",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "raiton_flash_bolt",
        "name": "Raiton: Flash Bolt",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "raiton_thunder_fist",
        "name": "Raiton: Thunder Fist",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "raiton_lightning_rain",
        "name": "Raiton: Lightning Rain",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "raiton_coil_serpent",
        "name": "Raiton: Coil Serpent",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "raiton_shock_net",
        "name": "Raiton: Shock Net",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "raiton_black_current_surge",
        "name": "Raiton: Black Current Surge",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "raiton_plasma_cutter",
        "name": "Raiton: Plasma Cutter",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "raiton_stormstep_cloak",
        "name": "Raiton: Stormstep Cloak",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "raiton_raijin_s_wrath",
        "name": "Raiton: Raijin's Wrath",
        "rank": "S",
        "type": "Ninjutsu",
        "element": "Raiton",
        "description": "No description available.",
        "chakra_cost": 150,
        "shop_cost": 15000
    },
    {
        "id": "f_ton_breeze_flick",
        "name": "Fūton: Breeze Flick",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "f_ton_wind_whisper",
        "name": "Fūton: Wind Whisper",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "f_ton_puff_step",
        "name": "Fūton: Puff Step",
        "rank": "E",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "f_ton_gale_shuriken",
        "name": "Fūton: Gale Shuriken",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "f_ton_cutter_palm",
        "name": "Fūton: Cutter Palm",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "f_ton_wind_veil",
        "name": "Fūton: Wind Veil",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "f_ton_dust_dance",
        "name": "Fūton: Dust Dance",
        "rank": "D",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "f_ton_wind_bullet",
        "name": "Fūton: Wind Bullet",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "f_ton_air_clone",
        "name": "Fūton: Air Clone",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "f_ton_crescent_slash",
        "name": "Fūton: Crescent Slash",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "f_ton_pressure_dome",
        "name": "Fūton: Pressure Dome",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "f_ton_vortex_fist",
        "name": "Fūton: Vortex Fist",
        "rank": "C",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "f_ton_razor_tempest",
        "name": "Fūton: Razor Tempest",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "f_ton_cyclone_bind",
        "name": "Fūton: Cyclone Bind",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "f_ton_whisper_step",
        "name": "Fūton: Whisper Step",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "f_ton_wind_scythe",
        "name": "Fūton: Wind Scythe",
        "rank": "B",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "f_ton_divine_gale_dance",
        "name": "Fūton: Divine Gale Dance",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "f_ton_vacuum_field",
        "name": "Fūton: Vacuum Field",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "f_ton_howling_typhoon",
        "name": "Fūton: Howling Typhoon",
        "rank": "A",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "f_ton_sky_severance",
        "name": "Fūton: Sky Severance",
        "rank": "S",
        "type": "Ninjutsu",
        "element": "Fuuton",
        "description": "No description available.",
        "chakra_cost": 150,
        "shop_cost": 15000
    },
    {
        "id": "henge_no_jutsu",
        "name": "Henge no Jutsu (Transformation Jutsu)",
        "rank": "E",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "kawarimi_no_jutsu",
        "name": "Kawarimi no Jutsu (Substitution Jutsu)",
        "rank": "E",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "bunshin_no_jutsu",
        "name": "Bunshin no Jutsu (Clone Jutsu)",
        "rank": "E",
        "type": "Ninjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "nawanuke_no_jutsu",
        "name": "Nawanuke no Jutsu (Escape Jutsu)",
        "rank": "E",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "kakuremino_no_jutsu",
        "name": "Kakuremino no Jutsu (Cloak of Invisibility)",
        "rank": "E",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 5,
        "shop_cost": 50
    },
    {
        "id": "kinobori",
        "name": "Kinobori (Tree Climbing Practice)",
        "rank": "D",
        "type": "Utility",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "suimen_hokou_no_gyou",
        "name": "Suimen Hokou no Gyou (Water Walking)",
        "rank": "D",
        "type": "Utility",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "shunshin_no_jutsu",
        "name": "Shunshin no Jutsu (Body Flicker)",
        "rank": "D",
        "type": "Ninjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "meisai_gakure_no_jutsu",
        "name": "Meisai Gakure no Jutsu (Camouflage Concealment)",
        "rank": "D",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "shuriken_kage_bunshin_no_jutsu",
        "name": "Shuriken Kage Bunshin no Jutsu (Shuriken Shadow Clone)",
        "rank": "D",
        "type": "Ninjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 10,
        "shop_cost": 150
    },
    {
        "id": "kage_bunshin_no_jutsu",
        "name": "Kage Bunshin no Jutsu (Shadow Clone Technique)",
        "rank": "C",
        "type": "Ninjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "chakra_suppression_technique",
        "name": "Chakra Suppression Technique",
        "rank": "C",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "kaif_no_jutsu",
        "name": "Kaifū no Jutsu (Unsealing Technique)",
        "rank": "C",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "f_in_chakra_tag_bind",
        "name": "Fūin: Chakra Tag Bind",
        "rank": "C",
        "type": "Fūinjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "medical_ninjutsu_minor_healing_touch",
        "name": "Medical Ninjutsu: Minor Healing Touch",
        "rank": "C",
        "type": "Medical Ninjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 20,
        "shop_cost": 500
    },
    {
        "id": "genjutsu_false_surroundings",
        "name": "Genjutsu: False Surroundings",
        "rank": "B",
        "type": "Genjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "f_in_chakra_lock_seal",
        "name": "Fūin: Chakra Lock Seal",
        "rank": "B",
        "type": "Fūinjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "sensory_perception_technique",
        "name": "Sensory Perception Technique",
        "rank": "B",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 40,
        "shop_cost": 1500
    },
    {
        "id": "taj_kage_bunshin_no_jutsu",
        "name": "Tajū Kage Bunshin no Jutsu (Multi Shadow Clone Jutsu)",
        "rank": "A",
        "type": "Ninjutsu",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 80,
        "shop_cost": 5000
    },
    {
        "id": "hiraishin_no_jutsu",
        "name": "Hiraishin no Jutsu (Flying Thunder God Technique)",
        "rank": "S",
        "type": "General",
        "element": None,
        "description": "No description available.",
        "chakra_cost": 150,
        "shop_cost": 15000
    }
]


print("Temporary script to generate JSON content created.") 