# Diccionario de partículas con estructura unificada
particles = {
    # Quarks
    'Up': {'mass': 2.3, 'unit': 'MeV/c²', 'charge': 2/3, 'spin': 1/2, 'family': 'Quark', 'binary': "00000000", 'color_name' : '\033[92mUp\033[0m', 'color_binary' : '\033[92m00000000\033[0m'},
    'Charm': {'mass': 1.28, 'unit': 'GeV/c²', 'charge': 2/3, 'spin': 1/2, 'family': 'Quark', 'binary': "00000001", 'color_name' : '\033[92mCharm\033[0m', 'color_binary' : '\033[92m00000001\033[0m'},
    'Top': {'mass': 173.1, 'unit': 'GeV/c²', 'charge': 2/3, 'spin': 1/2, 'family': 'Quark', 'binary': "00000010", 'color_name' : '\033[92mTop\033[0m', 'color_binary' : '\033[92m00000010\033[0m'},
    'Down': {'mass': 4.8, 'unit': 'MeV/c²', 'charge': -1/3, 'spin': 1/2, 'family': 'Quark', 'binary': "00000011", 'color_name' : '\033[92mDown\033[0m', 'color_binary' : '\033[92m00000011\033[0m'},
    'Strange': {'mass': 96, 'unit': 'MeV/c²', 'charge': -1/3, 'spin': 1/2, 'family': 'Quark', 'binary': "00000100", 'color_name' : '\033[92mStrange\033[0m', 'color_binary' : '\033[92m00000100\033[0m'},
    'Bottom': {'mass': 4.18, 'unit': 'GeV/c²', 'charge': -1/3, 'spin': 1/2, 'family': 'Quark', 'binary': "00000101", 'color_name' : '\033[92mBottom\033[0m', 'color_binary' : '\033[92m00000101\033[0m'},
    
    # Antiquarks
    'Antiup': {'mass': 2.3, 'unit': 'MeV/c²', 'charge': -2/3, 'spin': 1/2, 'family': 'Antiquark', 'binary': "00000110", 'color_name' : '\033[94mAntiup\033[0m', 'color_binary' : '\033[94m00000110\033[0m'},
    'Anticharm': {'mass': 1.28, 'unit': 'GeV/c²', 'charge': -2/3, 'spin': 1/2, 'family': 'Antiquark', 'binary': "00000111", 'color_name' : '\033[94mAnticharm\033[0m', 'color_binary' : '\033[94m00000111\033[0m'},
    'Antitop': {'mass': 173.1, 'unit': 'GeV/c²', 'charge': -2/3, 'spin': 1/2, 'family': 'Antiquark', 'binary': "00001000", 'color_name' : '\033[94mAntitop\033[0m', 'color_binary' : '\033[94m00001000\033[0m'},
    'Antidown': {'mass': 4.8, 'unit': 'MeV/c²', 'charge': 1/3, 'spin': 1/2, 'family': 'Antiquark', 'binary': "00001001", 'color_name' : '\033[94mAntidown\033[0m', 'color_binary' : '\033[94m00001001\033[0m'},
    'Antistrange': {'mass': 96, 'unit': 'MeV/c²', 'charge': 1/3, 'spin': 1/2, 'family': 'Antiquark', 'binary': "00001010", 'color_name' : '\033[94mAntistrange\033[0m', 'color_binary' : '\033[94m00001010\033[0m'},
    'Antibottom': {'mass': 4.18, 'unit': 'GeV/c²', 'charge': 1/3, 'spin': 1/2, 'family': 'Antiquark', 'binary': "00001011", 'color_name' : '\033[94mAntibottom\033[0m', 'color_binary' : '\033[94m00001011\033[0m'},
    
    # Leptons
    'Electron': {'mass': 0.511, 'unit': 'MeV/c²', 'charge': -1, 'spin': 1/2, 'family': 'Lepton', 'binary': "00001100", 'color_name' : '\033[95mElectron\033[0m', 'color_binary' : '\033[95m00001100\033[0m'},
    'Muon': {'mass': 105.7, 'unit': 'MeV/c²', 'charge': -1, 'spin': 1/2, 'family': 'Lepton', 'binary': "00001101", 'color_name' : '\033[95mMuon\033[0m', 'color_binary' : '\033[95m00001101\033[0m'},
    'Tau': {'mass': 1.7768, 'unit': 'GeV/c²', 'charge': -1, 'spin': 1/2, 'family': 'Lepton', 'binary': "00001110", 'color_name' : '\033[95mTau\033[0m', 'color_binary' : '\033[95m00001110\033[0m'},
    'Electronneutrino': {'mass': 2.2, 'unit': 'eV/c²', 'charge': 0, 'spin': 1/2, 'family': 'Lepton', 'binary': "00001111", 'color_name' : '\033[95mElectronneutrino\033[0m', 'color_binary' : '\033[95m00001111\033[0m'},
    'Muonneutrino': {'mass': 0.17, 'unit': 'MeV/c²', 'charge': 0, 'spin': 1/2, 'family': 'Lepton', 'binary': "00010000", 'color_name' : '\033[95mMuonneutrino\033[0m', 'color_binary' : '\033[95m00010000\033[0m'},
    'Tauneutrino': {'mass': 18.2, 'unit': 'MeV/c²', 'charge': 0, 'spin': 1/2, 'family': 'Lepton', 'binary': "00010001", 'color_name' : '\033[95mTauneutrino\033[0m', 'color_binary' : '\033[95m00010001\033[0m'},
    
    # Antileptons
    'Positron': {'mass': 0.511, 'unit': 'MeV/c²', 'charge': 1, 'spin': 1/2, 'family': 'Antilepton', 'binary': "00010010", 'color_name' : '\033[96mPositron\033[0m', 'color_binary' : '\033[96m00010010\033[0m'},
    'Antimuon': {'mass': 105.7, 'unit': 'MeV/c²', 'charge': 1, 'spin': 1/2, 'family': 'Antilepton', 'binary': "00010011", 'color_name' : '\033[96mAntimuon\033[0m', 'color_binary' : '\033[96m00010011\033[0m'},
    'Antitau': {'mass': 1.7768, 'unit': 'GeV/c²', 'charge': 1, 'spin': 1/2, 'family': 'Antilepton', 'binary': "00010100", 'color_name' : '\033[96mAntitau\033[0m', 'color_binary' : '\033[96m00010100\033[0m'},
    'Electronantineutrino': {'mass': 2.2, 'unit': 'eV/c²', 'charge': 0, 'spin': 1/2, 'family': 'Antilepton', 'binary': "00010101", 'color_name' : '\033[96mElectronantineutrino\033[0m', 'color_binary' : '\033[96m00010101\033[0m'},
    'Muonantineutrino': {'mass': 0.17, 'unit': 'MeV/c²', 'charge': 0, 'spin': 1/2, 'family': 'Antilepton', 'binary': "00010110", 'color_name' : '\033[96mMuonantineutrino\033[0m', 'color_binary' : '\033[96m00010110\033[0m'},
    'Tauantineutrino': {'mass': 18.2, 'unit': 'MeV/c²', 'charge': 0, 'spin': 1/2, 'family': 'Antilepton', 'binary': "00010111", 'color_name' : '\033[96mTauantineutrino\033[0m', 'color_binary' : '\033[96m00010111\033[0m'},
    
    # Gauge Bosons
    'Gluon': {'mass': 0, 'unit': 'MeV/c²', 'charge': 0, 'spin': 1, 'family': 'Gauge Boson', 'binary': "00011000", 'color_name' : '\033[101mGluon\033[0m', 'color_binary' : '\033[101m00011000\033[0m'},
    'Photon': {'mass': 0, 'unit': 'MeV/c²', 'charge': 0, 'spin': 1, 'family': 'Gauge Boson', 'binary': "00011001", 'color_name' : '\033[101mPhoton\033[0m', 'color_binary' : '\033[101m00011001\033[0m'},
    'BosonZ': {'mass': 91.2, 'unit': 'GeV/c²', 'charge': 0, 'spin': 1, 'family': 'Gauge Boson', 'binary': "00011010", 'color_name' : '\033[101mBosonZ\033[0m', 'color_binary' : '\033[101m00011010\033[0m'},
    'BosonWplus': {'mass': 80.4, 'unit': 'GeV/c²', 'charge': 1, 'spin': 1, 'family': 'Gauge Boson', 'binary': "00011011", 'color_name' : '\033[101mBosonWplus\033[0m', 'color_binary' : '\033[101m00011011\033[0m'},
    'BosonWless': {'mass': 80.4, 'unit': 'GeV/c²', 'charge': -1, 'spin': 1, 'family': 'Gauge Boson', 'binary': "00011100", 'color_name' : '\033[101mBosonWless\033[0m', 'color_binary' : '\033[101m00011100\033[0m'},
    'Graviton': {'mass': 0, 'unit': 'GeV/c²', 'charge': 0, 'spin': 2, 'family': 'Gauge Boson', 'binary': "00011101", 'color_name' : '\033[101mGraviton\033[0m', 'color_binary' : '\033[101m00011101\033[0m'},
    
    # Scalar Bosons
    'Higgs': {'mass': 126, 'unit': 'GeV/c²', 'charge': 0, 'spin': 0, 'family': 'Scalar Boson', 'binary': "00011110", 'color_name' : '\033[102mHiggs\033[0m', 'color_binary' : '\033[102m00011110\033[0m'}
}

# Constantes físicas
GeV = 1_000_000_000  # eV
MeV = 1_000_000      # eV
eV = 0.0000000000000000001602176634  # J (valor exacto desde 2019)
c = 299_792_458       # m/s
c_square = c ** 2

def convert_mass_to_eV(mass_value, from_unit):
    """Convierte la masa a eV/c²"""
    if from_unit == 'GeV/c²':
        return mass_value * GeV
    elif from_unit == 'MeV/c²':
        return mass_value * MeV
    elif from_unit == 'eV/c²':
        return mass_value
    else:
        raise ValueError(f"Unidad no reconocida: {from_unit}")

def convert_mass_to_kg(mass_eV):
    """Convierte masa en eV/c² a kilogramos"""
    # m = (E/c²) donde E está en eV convertidos a joules
    energy_joules = mass_eV * eV  # E en joules
    mass_kg = energy_joules / c_square  # m = E/c²
    return mass_kg

# Recorrer todas las partículas y convertir sus masas a kilogramos
for particle_name, properties in particles.items():
    mass_value = properties['mass']
    unit = properties['unit']
    
    # Solo convertir si la masa no es cero
    if mass_value > 0:
        # Convertir a eV primero
        mass_eV = convert_mass_to_eV(mass_value, unit)
        # Convertir a kilogramos
        mass_kg = convert_mass_to_kg(mass_eV)
        
        print(f"{particle_name}: {mass_value} {unit} = {mass_kg} kg")
    else:
        print(f"{particle_name}: 0 {unit} = 0 kg (partícula sin masa)")
        
