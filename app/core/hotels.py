from dataclasses import dataclass


@dataclass(frozen=True)
class HotelSheet:
    scrape_id: int
    name: str
    short_form: str
    spreadsheet_id: str
    sheet_gid: int

    @property
    def sheet_range(self) -> str:
        return f"gid={self.sheet_gid}!A:Z"


HOTELS: dict[int, HotelSheet] = {
    4: HotelSheet(
        scrape_id=4,
        name="Indigo London Paddington",
        short_form="HILP",
        spreadsheet_id="1jbcohYRvmxbs3ME8qR5UF12QH5x5_uGQhBrJ2Xt6baI",
        sheet_gid=1051183713,
    ),
    3: HotelSheet(
        scrape_id=3,
        name="Mercure London Paddington",
        short_form="MLP",
        spreadsheet_id="1UBSUzGhELZNnJyJb_Xxj_q_HSpX2T9YRqcXROQ_-uVo",
        sheet_gid=15605064,
    ),
    6: HotelSheet(
        scrape_id=6,
        name="Mercure London Hyde Park",
        short_form="MLHP",
        spreadsheet_id="13odyzHEUn5vJBkhH33piqfUIrthNfAU06AlVGuUmK90",
        sheet_gid=1540929876,
    ),
    7: HotelSheet(
        scrape_id=7,
        name="Holiday Inn Leicester Wigston",
        short_form="HILW",
        spreadsheet_id="1vLmXFRV-qhEzIDTKx2mRkOXCA9VJTmWbjLjyuF2aSJ8",
        sheet_gid=1051183713,
    ),
}