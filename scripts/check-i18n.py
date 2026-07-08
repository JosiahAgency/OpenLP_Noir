#!/usr/bin/env python
# vim: autoindent shiftwidth=4 expandtab textwidth=120 tabstop=4 softtabstop=4

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008 OpenLP Developers                                   #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
import sys
import xml.etree.ElementTree as ET
from argparse import ArgumentParser, Namespace
from pathlib import Path


def get_args() -> Namespace:
    """Get the command line arguments"""
    parser = ArgumentParser()
    parser.add_argument('-b', '--base-path', help='Base path containing all the translation files', required=True)
    return parser.parse_args()


def find_variables(text: str) -> set[str]:
    """Find the variables in a string"""
    variables = set()
    remaining_text = text
    start_idx = remaining_text.find('{')
    while start_idx >= 0:
        end_idx = remaining_text.find('}')
        variables.add(remaining_text[start_idx:end_idx + 1])
        remaining_text = remaining_text[end_idx + 1:]
        start_idx = remaining_text.find('{')
    return variables


def check_for_mismatching_variables(xml_file: Path) -> list[dict[str, str]]:
    """Load an XML file and check it for mismatched variables, returning any errors"""
    errors: list[dict[str, str]] = []

    tree = ET.parse(xml_file)
    root = tree.getroot()

    messages = root.findall('.//context/message')
    for message in messages:
        source = message.find('source').text
        if source is None:
            source = ""
        source = source.strip()        # type: ignore[union-attr]
        translation = message.find('translation').text      # type: ignore[union-attr]
        if translation is None:
            continue
        else:
            translation = translation.strip()

        if '{' not in source or source == '{ And }':
            continue

        # Find text between "{" and "}" in source
        # set(source[source.find('{')+1:source.find('}')].split())
        source_variables = find_variables(source)

        # Find text between "{" and "}" in translation
        # set(translation[translation.find('{')+1:translation.find('}')].split())
        translation_variables = find_variables(translation)

        # Check if the same text exists in both source and translation
        if source_variables != translation_variables:
            errors.append({'source': source, 'translation': translation})

    return errors


def main():
    """Run through all the i18n files and check that the variables in the translation match the source"""
    exit_code = 0
    args = get_args()
    xml_files = Path(args.base_path).glob('*.ts')
    for ts_file in xml_files:
        print(f"processing: {ts_file}")
        errors = check_for_mismatching_variables(ts_file)
        if errors:
            exit_code = 1
            print('=========================================')
            print('Found errors in %s' % ts_file)
            for error in errors:
                print('>', error['source'])
                print('<', error['translation'])
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
