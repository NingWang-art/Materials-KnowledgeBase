TABLE_POLYMER_PROPERTY_NAME = 'polym00'
PAPER_METADATA_TABLE_NAME = '690hd00'
PAPER_TEXT_TABLE_NAME = '690hd02'
TABLE_FILED_INFO_NAME = '690hd14'
TABLE_PAPER_MONOMER_INFO_NAME = '690hd16'
TABLE_MONOMER_INFO_NAME = '690hd17'
TABLE_EPOXY_VISCOSITY_NAME = '677df00'

POLYMER_DB_TABLES = {
    'tables': [
        {
            'table_name': TABLE_POLYMER_PROPERTY_NAME,
            'description': 'Polymers information reported in the paper, including polymer names, types, compositions, properties, and corresponding paper DOI.',
        },
        {
            'table_name': PAPER_METADATA_TABLE_NAME,
            'description': 'Metadata about papers, including their titles, abstracts, authors, publication dates, journal information, DOI, etc.',
        },
        {
            'table_name': PAPER_TEXT_TABLE_NAME,
            'description': 'The full text of the paper and SI, also have DOI',
        },
        {
            'table_name': TABLE_PAPER_MONOMER_INFO_NAME,
            'description': 'Monomers information reported in the paper, including their abbreviations, full_name, SMILES, note and paper DOI. Only query this table when the paper is specified. Be careful to query the abbreviation or full name.',
        },
        {
            'table_name': TABLE_MONOMER_INFO_NAME,
            'description': 'Structure information of monomers, including their abbreviations, full_name, note, SMILES. If the paper is not specified when querying the monomer, this table should be queried first. Be careful to query the abbreviation or full name.',
        },
        {
            'table_name': TABLE_EPOXY_VISCOSITY_NAME,
            'description': 'Structure information of the viscosity of epoxy resin, including monomer names, SMILES, ratios, and the temperature of viscosity measurements.Query this table when the viscosity of epoxy resin is involved.',
            'fields': ['Temperature', 'Viscosity', 'compound_0', 'compound_1', 'smiles_0', 'smiles_1', 'ratio_0', 'ratio_1', 'formulation_id'],
            'primary_fields': ['Temperature', 'Viscosity', 'compound_0', 'compound_1', 'smiles_0', 'smiles_1', 'ratio_0', 'ratio_1', 'formulation_id'],
        },

    ],
    'paper_text_table': PAPER_TEXT_TABLE_NAME,
    'paper_figure_table': None,
    'field_info_table': TABLE_FILED_INFO_NAME,
}
