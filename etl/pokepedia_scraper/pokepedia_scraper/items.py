"""Scrapy items for InfiniDex Pokepedia moveset scraper."""

import scrapy


class MovesetItem(scrapy.Item):
    """
    One move-learning rule for one Pokémon.

    Fields:
        pokemon_name_fr  (str)       : Pokepedia page name (FR), used as scraping key
        pokemon_if_id    (int)       : IF internal Pokémon ID
        move_name_fr     (str)       : Move name as displayed on Pokepedia (FR)
        method           (str)       : 'level_up' | 'tm' | 'tutor' | 'breeding'
        level            (int|None)  : Learn level (level_up only)
        source           (str)       : Always 'base' — IF overrides applied later
    """

    pokemon_name_fr = scrapy.Field()
    pokemon_if_id   = scrapy.Field()
    move_name_fr    = scrapy.Field()
    method          = scrapy.Field()
    level           = scrapy.Field()
    source          = scrapy.Field()

    def validate(self):
        for field in ("pokemon_if_id", "move_name_fr", "method"):
            if not self.get(field):
                raise ValueError(f"Missing required field: {field}")
        if self.get("level") is not None:
            try:
                self["level"] = int(self["level"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid level: {self['level']}") from exc
        return self
