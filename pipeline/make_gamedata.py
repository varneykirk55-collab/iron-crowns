"""Writes the data-driven game definitions: nations.json, eras.json, units.json."""
import json, os
OUT = os.path.join(os.path.dirname(__file__), '..', 'game', 'data')
# code: (color, aggression 0..1, diplomacy 0..1, flag spec)
N = {
 'USA': ('#3d5a9e', .55, .6, ['canton', '#b22234', '#ffffff', '#3c3b6e']), 'CAN': ('#c8453c', .2, .7, ['pale', '#d52b1e', '#ffffff', '#d52b1e']),
 'MEX': ('#3b8a55', .4, .5, ['pale', '#006847', '#ffffff', '#ce1126']), 'BRA': ('#3f9e4a', .4, .5, ['disc', '#009c3b', '#ffdf00']),
 'ARG': ('#78aee0', .45, .5, ['fess', '#74acdf', '#ffffff', '#74acdf']), 'COL': ('#e0c040', .4, .5, ['fess', '#fcd116', '#003893', '#ce1126']),
 'PER': ('#c0504d', .4, .5, ['pale', '#d91023', '#ffffff', '#d91023']), 'CHL': ('#a93a4a', .45, .5, ['fess', '#ffffff', '#ffffff', '#d52b1e']),
 'VEN': ('#d9a23c', .45, .4, ['fess', '#ffcc00', '#00247d', '#cf142b']),
 'GBR': ('#c23b3b', .6, .6, ['cross', '#012169', '#ffffff', '#c8102e']), 'FRA': ('#4a6fc8', .6, .6, ['pale', '#0055a4', '#ffffff', '#ef4135']),
 'DEU': ('#6b6b6b', .65, .5, ['fess', '#000000', '#dd0000', '#ffce00']), 'ITA': ('#4aa35a', .5, .5, ['pale', '#009246', '#ffffff', '#ce2b37']),
 'ESP': ('#e0a030', .5, .5, ['fess', '#aa151b', '#f1bf00', '#aa151b']), 'RUS': ('#3f8a5c', .7, .4, ['fess', '#ffffff', '#0039a6', '#d52b1e']),
 'POL': ('#d65a6a', .45, .55, ['fess', '#ffffff', '#ffffff', '#dc143c']), 'SWE': ('#2f7fc1', .45, .65, ['cross', '#006aa7', '#fecc00', '#fecc00']),
 'NOR': ('#b04a4a', .35, .6, ['cross', '#ba0c2f', '#ffffff', '#00205b']), 'FIN': ('#f0f0f0', .35, .6, ['cross', '#ffffff', '#ffffff', '#002f6c']),
 'DNK': ('#d04040', .35, .65, ['cross', '#c8102e', '#ffffff', '#ffffff']), 'NLD': ('#e07830', .35, .7, ['fess', '#ae1c28', '#ffffff', '#21468b']),
 'TUR': ('#a83232', .6, .45, ['disc', '#e30a17', '#ffffff']), 'UKR': ('#e8d34a', .4, .5, ['fess', '#0057b7', '#0057b7', '#ffd700']),
 'GRC': ('#5f8ed0', .4, .55, ['fess', '#0d5eaf', '#ffffff', '#0d5eaf']), 'ROU': ('#d0b040', .4, .5, ['pale', '#002b7f', '#fcd116', '#ce1126']),
 'PRT': ('#3a7a3a', .4, .6, ['pale', '#006600', '#ff0000', '#ff0000']), 'AUT': ('#e8e0d0', .45, .6, ['fess', '#ed2939', '#ffffff', '#ed2939']),
 'CHN': ('#d8b030', .6, .45, ['canton', '#de2910', '#de2910', '#ffde00']), 'JPN': ('#e8e8e8', .55, .55, ['disc', '#ffffff', '#bc002d']),
 'IND': ('#e09050', .45, .55, ['fess', '#ff9933', '#ffffff', '#138808']), 'KOR': ('#7a9ac8', .35, .6, ['disc', '#ffffff', '#cd2e3a']),
 'IDN': ('#b05050', .4, .5, ['fess', '#ce1126', '#ce1126', '#ffffff']), 'IRN': ('#4a9a6a', .55, .4, ['fess', '#239f40', '#ffffff', '#da0000']),
 'SAU': ('#2e7d32', .45, .45, ['fess', '#006c35', '#006c35', '#006c35']), 'PAK': ('#2a6a3a', .5, .45, ['disc', '#01411c', '#ffffff']),
 'THA': ('#6a5acd', .4, .55, ['fess', '#a51931', '#2d2a4a', '#a51931']), 'VNM': ('#c04848', .5, .45, ['disc', '#da251d', '#ffff00']),
 'PHL': ('#5a7ab8', .3, .55, ['fess', '#0038a8', '#ffffff', '#ce1126']), 'KAZ': ('#5ab0c8', .4, .5, ['disc', '#00afca', '#fec50c']),
 'EGY': ('#c8b060', .5, .45, ['fess', '#ce1126', '#ffffff', '#000000']), 'NGA': ('#3aa05a', .45, .45, ['pale', '#008751', '#ffffff', '#008751']),
 'ZAF': ('#b8863b', .45, .5, ['fess', '#de3831', '#ffffff', '#002395']), 'ETH': ('#7aa040', .45, .45, ['fess', '#078930', '#fcdd09', '#da121a']),
 'DZA': ('#4a8a50', .45, .45, ['pale', '#006233', '#ffffff', '#ffffff']), 'MAR': ('#a04040', .4, .5, ['disc', '#c1272d', '#006233']),
 'AUS': ('#4060a0', .4, .6, ['canton', '#00008b', '#00008b', '#ffffff']), 'NZL': ('#304878', .3, .6, ['canton', '#00247d', '#00247d', '#cc142b']),
}
PLAYABLE = ['USA', 'SWE', 'JPN']
nations = {'playable': PLAYABLE, 'majors': [
    {'code': k, 'color': v[0], 'aggression': v[1], 'diplomacy': v[2], 'flag': v[3], 'playable': k in PLAYABLE} for k, v in N.items()],
    'minor_color_seed': 7, 'notes': 'Countries not listed here are minor polities: they defend and accept peace but never start wars.'}
eras = {'eras': [
    {'id': 'medieval', 'name': 'Medieval Age', 'start': 1300, 'productivity': 1.0, 'move_km_day': 22, 'naval_range': 1, 'siege_days': 120, 'battle_range_mult': 1.0},
    {'id': 'early_modern', 'name': 'Age of Pike and Shot', 'start': 1500, 'productivity': 1.6, 'move_km_day': 26, 'naval_range': 4, 'siege_days': 90, 'battle_range_mult': 1.0},
    {'id': 'c19', 'name': 'Age of Revolutions', 'start': 1800, 'productivity': 3.0, 'move_km_day': 35, 'naval_range': 10, 'siege_days': 60, 'battle_range_mult': 1.0},
    {'id': 'c20', 'name': 'Age of Mechanised War', 'start': 1914, 'productivity': 6.0, 'move_km_day': 60, 'naval_range': 30, 'siege_days': 40, 'battle_range_mult': 1.0},
    {'id': 'modern', 'name': 'Modern Era', 'start': 1980, 'productivity': 10.0, 'move_km_day': 90, 'naval_range': 99, 'siege_days': 30, 'battle_range_mult': 1.0}],
    'start_years': [1300, 1500, 1800, 1914, 1980]}
# role: inf / ranged / cav / art / armor ; model: VAT or static asset id
U = []
def u(id, era, name, role, model, kind, men, cost, upkeep, res, melee, defense, rng, fire_int, acc, lethal, armor, speed, morale, cap=None):
    U.append(dict(id=id, era=era, name=name, role=role, model=model, kind=kind, men=men, cost=cost, upkeep=upkeep, resources=res,
                  melee=melee, defense=defense, range=rng, fire_interval=fire_int, accuracy=acc, lethality=lethal, armor=armor,
                  speed=speed, morale=morale, visual_men=cap or 64))
u('levy_spear', 'medieval', 'Spear Levy', 'inf', 'med_spear', 'vat', 1000, 60, 2.0, {}, 9, 11, 0, 0, 0, 0, 0.15, 1.4, 55)
u('archers', 'medieval', 'Bowmen', 'ranged', 'med_archer', 'vat', 800, 80, 2.6, {'timber': 1}, 5, 6, 140, 4.0, 0.10, 0.45, 0.05, 1.5, 50)
u('knights', 'medieval', 'Mounted Knights', 'cav', 'med_knight', 'cav', 400, 180, 6.0, {'iron': 1, 'horses': 2}, 20, 14, 0, 0, 0, 0, 0.45, 4.5, 75, 32)
u('bombard', 'medieval', 'Bombards', 'art', 'art_bombard', 'gun', 120, 160, 4.0, {'iron': 2}, 2, 3, 260, 9.0, 0.30, 1.0, 0.0, 0.6, 45, 4)
u('pike', 'early_modern', 'Pike Square', 'inf', 'em_pike', 'vat', 1200, 90, 2.6, {'timber': 1}, 12, 16, 0, 0, 0, 0, 0.2, 1.4, 62)
u('musketeers', 'early_modern', 'Musketeers', 'ranged', 'em_musket', 'vat', 1000, 110, 3.0, {'iron': 1}, 6, 7, 110, 6.0, 0.11, 0.6, 0.05, 1.4, 55)
u('cuirassiers', 'early_modern', 'Cuirassiers', 'cav', 'em_cuirassier', 'cav', 500, 220, 7.0, {'iron': 1, 'horses': 2}, 22, 14, 0, 0, 0, 0, 0.35, 4.6, 72, 32)
u('culverins', 'early_modern', 'Field Culverins', 'art', 'art_cannon', 'gun', 150, 200, 4.5, {'iron': 2}, 2, 3, 320, 7.0, 0.35, 1.0, 0.0, 0.6, 45, 4)
u('line_inf', 'c19', 'Line Infantry', 'ranged', 'c19_line', 'vat', 1200, 140, 3.4, {'iron': 1}, 9, 9, 130, 4.0, 0.12, 0.65, 0.0, 1.5, 62)
u('grenadiers', 'c19', 'Grenadiers', 'inf', 'c19_line', 'vat', 900, 160, 3.8, {'iron': 1}, 15, 13, 100, 6.0, 0.08, 0.6, 0.0, 1.6, 75)
u('hussars', 'c19', 'Hussars', 'cav', 'c19_hussar', 'cav', 600, 240, 7.0, {'horses': 2}, 21, 11, 0, 0, 0, 0, 0.1, 5.0, 70, 32)
u('field_guns', 'c19', 'Field Artillery', 'art', 'art_cannon', 'gun', 200, 260, 5.0, {'iron': 3}, 2, 4, 420, 5.0, 0.40, 1.0, 0.0, 0.7, 50, 4)
u('riflemen', 'c20', 'Rifle Infantry', 'ranged', 'c20_rifle', 'vat', 1500, 200, 4.0, {'iron': 1}, 10, 12, 220, 3.0, 0.10, 0.8, 0.05, 1.6, 65)
u('tanks_c20', 'c20', 'Tank Battalion', 'armor', 'tank_c20', 'veh', 300, 520, 12.0, {'iron': 3, 'coal': 1, 'oil': 3}, 18, 30, 300, 3.5, 0.30, 4.0, 0.7, 3.2, 80, 6)
u('howitzers', 'c20', 'Howitzer Battery', 'art', 'art_howitzer', 'gun', 300, 380, 7.0, {'iron': 4}, 2, 5, 600, 4.0, 0.45, 2.2, 0.0, 0.8, 55, 4)
u('trucks_inf', 'c20', 'Motorised Infantry', 'ranged', 'c20_rifle', 'vat', 1200, 300, 6.0, {'oil': 2, 'iron': 1}, 10, 12, 220, 3.0, 0.10, 0.8, 0.05, 2.4, 68)
u('mech_inf', 'modern', 'Mechanised Infantry', 'ranged', 'mod_rifle', 'vat', 1000, 450, 8.0, {'oil': 2, 'iron': 2}, 12, 16, 300, 2.0, 0.12, 1.0, 0.15, 2.2, 75)
u('mbt', 'modern', 'Main Battle Tanks', 'armor', 'mbt_modern', 'veh', 250, 900, 18.0, {'oil': 4, 'iron': 5}, 24, 45, 450, 3.0, 0.45, 6.0, 0.8, 4.0, 85, 6)
u('ifv', 'modern', 'IFV Company', 'armor', 'ifv_modern', 'veh', 300, 600, 12.0, {'oil': 3, 'iron': 3}, 14, 26, 350, 1.5, 0.25, 2.5, 0.55, 4.2, 78, 6)
u('rocket_art', 'modern', 'Artillery Battalion', 'art', 'art_howitzer', 'gun', 300, 650, 12.0, {'iron': 5}, 2, 6, 800, 3.0, 0.55, 3.0, 0.0, 1.0, 60, 4)
units = {'units': U, 'era_tier': {'medieval': 0, 'early_modern': 1, 'c19': 2, 'c20': 3, 'modern': 4},
         'resources': ['grain', 'timber', 'iron', 'oil', 'gold', 'horses', 'fish', 'coal'], 'resource_price': 2.0}
for name, obj in (('nations', nations), ('eras', eras), ('units', units)):
    json.dump(obj, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
print('ok', len(N), len(U))
