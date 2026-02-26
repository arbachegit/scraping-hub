/**
 * Utilities for normalizing politician names from TSE raw data
 * and mapping IBGE codes to UF abbreviations.
 */

const LOWERCASE_WORDS = new Set(['da', 'de', 'do', 'dos', 'das', 'e']);

/**
 * Normalizes a raw politician name from TSE (ALL CAPS, numbers, dots, hyphens)
 * into proper Title Case.
 *
 * Examples:
 *   "JOSE DA SILVA 45" → "Jose da Silva"
 *   "MARIA.DOS.SANTOS" → "Maria dos Santos"
 *   "JOAO - PEREIRA" → "Joao Pereira"
 */
export function normalizePoliticianName(raw: string | null | undefined): string {
  if (!raw) return '';

  const cleaned = raw
    .replace(/\d+/g, '')        // remove numbers
    .replace(/[._]+/g, ' ')     // dots/underscores → space
    .replace(/-+/g, ' ')        // hyphens → space
    .replace(/\s+/g, ' ')       // collapse multiple spaces
    .trim();

  if (!cleaned) return '';

  return cleaned
    .toLowerCase()
    .split(' ')
    .filter((w) => w.length > 0)
    .map((word, index) => {
      if (index > 0 && LOWERCASE_WORDS.has(word)) {
        return word;
      }
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(' ');
}

/**
 * Maps the first 2 digits of a 7-digit IBGE code to its UF abbreviation.
 */
const IBGE_UF_MAP: Record<string, string> = {
  '11': 'RO',
  '12': 'AC',
  '13': 'AM',
  '14': 'RR',
  '15': 'PA',
  '16': 'AP',
  '17': 'TO',
  '21': 'MA',
  '22': 'PI',
  '23': 'CE',
  '24': 'RN',
  '25': 'PB',
  '26': 'PE',
  '27': 'AL',
  '28': 'SE',
  '29': 'BA',
  '31': 'MG',
  '32': 'ES',
  '33': 'RJ',
  '35': 'SP',
  '41': 'PR',
  '42': 'SC',
  '43': 'RS',
  '50': 'MS',
  '51': 'MT',
  '52': 'GO',
  '53': 'DF',
};

export function ibgeToUF(codigoIbge: string | number | null | undefined): string {
  if (codigoIbge == null) return '';
  const code = String(codigoIbge);
  if (code.length < 2) return '';
  return IBGE_UF_MAP[code.slice(0, 2)] || '';
}
