import re
import sys
from tqdm import tqdm

from lxml import etree

from database_manager import DatabaseManager


def parse(dblp_file, database_path="aip"):
    database = DatabaseManager(location=database_path)

    hash, parsed = database.did_parse_file(dblp_file)
    if parsed:
        return True

    counter = 0  # counter for new keys.

    # dtd = etree.DTD(file="/media/lfdversluis/datastore/dblp.dtd")
    for event, element in tqdm(etree.iterparse(dblp_file, load_dtd=True,
                                               dtd_validation=True)):
        if element.tag not in ['article', 'inproceedings', 'proceedings']:
            continue

        if 'key' in element.attrib:
            id = str(element.attrib['key'])
        else:
            id = "id" + str(counter)
            print("new key added")
            counter += 1
        title = element.find('title')  # type: Optional[str]
        if title is not None:
            title = str(title.text).rstrip(".")
        year = element.find('year')  # type: Optional[int]
        if year is not None:
            try:
                year = int(re.search(r'\d+', str(year.text)).group())
                if 20 < year < 100:  # Weird cases like 92-93
                    year += 1900
                elif year < 20:  # weird cases like '12
                    year += 2000
            except:
                year = None
        volume = element.find('volume')  # type: Optional[int]
        if volume is not None:
            try:
                volume = int(volume.text)
            except:
                volume = None
        # authors = element.find('author')  # type: Optional[str]
        venue = element.find('booktitle')  # type: Optional[str]
        if venue is None and len(element.findall('journal')) > 0:
            venue = element.find('journal')

        if venue is not None and venue.text is not None:
            venue = str(venue.text)
        else:
            venue = None

        doi = None
        for ee in element.findall('ee'):
            ee_str = str(ee.text)
            if ee is not None and "doi.org" in ee_str:
                doi = ee_str[ee_str.index("doi.org/") + len("doi.org/"):]
                break

        if title is not None and year is not None and venue is not None:
            # Clean the title which may have HTML elements
            addedPaper = \
                database.update_or_insert_paper(id=id, doi=doi,
                                            title=title, abstract="",
                                            raw_venue_string=venue,
                                            year=year,
                                            volume=volume)

            # Get the authors for this paper and add them to the database
            authors = []  # tuples of ID, orcid, position
            for i, author_element in enumerate(element.findall('author')):
                orcid = None
                if "orcid" in author_element.attrib:
                    orcid = str(author_element.attrib['orcid'])

                # print(DatabaseManager.sanitize_string(
                # author_element.text.encode("ISO-8859-1"))) authors.append(
                # (DatabaseManager.sanitize_string(
                # author_element.text.encode("utf-8")), orcid)) print(
                # author_element.text)
                authors.append((author_element.text, orcid, i+1))

            if addedPaper:
                database.add_authors_for_article(authors=authors,
                                                 article_id=id)

        element.clear()

        # database.flush_missing_venues()
    database.add_parsed_file(hash)
    database.close()
    return True


if __name__ == '__main__':
    xml_file = "C:/Users/ktoka/Desktop/CSE2020-21/Y2Q4SP/raw-data/dblp2021.xml"
    # xml_file = "c:/Users/L/Downloads/dblp-2021-04-01.xml"
    if len(sys.argv) == 2:
        xml_file = sys.argv[1]

    parse(xml_file)
    print("Done parsing DBLP")
