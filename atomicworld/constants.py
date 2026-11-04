"""Constantes físicas y químicas usadas en los cálculos."""

# Número de Avogadro (valor exacto desde la redefinición del SI de 2019), en mol⁻¹
AVOGADRO = 6.02214076e23

# Quarks de valencia en cada nucleón: protón = uud, neutrón = udd
QUARKS_PER_PROTON = {"up": 2, "down": 1}
QUARKS_PER_NEUTRON = {"up": 1, "down": 2}

# Masas en reposo de los nucleones (CODATA 2018), en MeV/c²
PROTON_MASS_MEV = 938.27208816
NEUTRON_MASS_MEV = 939.56542052

# Bits por byte en la simulación del Big Bang
BITS_PER_BYTE = 8
