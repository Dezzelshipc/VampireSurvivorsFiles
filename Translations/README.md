# Translation file

Ripped from game files (I2Languages.asset): [I2Languages.yaml](I2Languages.yaml).

List of languages is under key '**mLanguages**'.

Based on that file were generated other formats:

* Converted to JSON: [I2Languages.json](Generated/I2Languages.json)
* Every entry key is in format: **'lang type'/{'subject (optional)'}'property'**
  (e.g. _characterLang/{ANTONIO}charName_ or _lang/intro_start_). So file can be split by lang types:
    * [LangList](Generated/Split/LangList): **'lang type'.json** file in format 
      { subject: property: list\[str] }
    * [LangDictionary](Generated/Split/LangDictionary): **'lang type'.json** file in format
      { subject: property: lang: str }
    * [InverseLangDictionary](Generated/Split/InverseLangDictionary): **'lang type'.json** file in format
      { lang: subject: property: str }