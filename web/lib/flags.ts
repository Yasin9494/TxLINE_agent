// Team -> ISO code for flagcdn.com images (reliable everywhere, unlike emoji flags).
export const FLAGS: Record<string, string> = {
  Argentina: "ar", Spain: "es", Austria: "at", USA: "us", "United States": "us",
  "Bosnia & Herzegovina": "ba", "Cape Verde": "cv", Australia: "au", Egypt: "eg",
  Colombia: "co", Ghana: "gh", Vietnam: "vn", Myanmar: "mm", Croatia: "hr",
  Germany: "de", Paraguay: "py", Portugal: "pt", England: "gb-eng", France: "fr",
  Brazil: "br", Netherlands: "nl", Morocco: "ma", Mexico: "mx", Iran: "ir",
  "Saudi Arabia": "sa", Belgium: "be", "New Zealand": "nz", Jordan: "jo",
  Algeria: "dz", Panama: "pa", Canada: "ca", Japan: "jp", "Korea Republic": "kr",
  "South Korea": "kr", Senegal: "sn", Uruguay: "uy", Switzerland: "ch", Poland: "pl",
  Denmark: "dk", Serbia: "rs", Ecuador: "ec", Qatar: "qa", Tunisia: "tn",
  Nigeria: "ng", Cameroon: "cm", Italy: "it", Norway: "no", Ukraine: "ua",
  Turkey: "tr", "Ivory Coast": "ci", Peru: "pe", Chile: "cl", Scotland: "gb-sct", Wales: "gb-wls",
};
export const flagUrl = (name: string) => {
  const c = FLAGS[name];
  return c ? `https://flagcdn.com/w80/${c}.png` : null;
};
