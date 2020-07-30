import argparse
from enum import Enum
from pathlib import Path
from subprocess import run, PIPE, call
import json
import tempfile, os
import ast
import re
import curses
from lib.interactive import UI
from gupy.view import ListViewDataSource

BLOCK_LEVEL = 2
TRANSLATION_DIRECTORY = '/Users/kober/code/java/taloom/just-hire-angular/src/app/commons/provider/translation/resources'
TRANSLATION_PATTERN = '*.properties.ts'

class Diff(Enum):
    ADDED = 1
    UPDATED = 2
    DELETED = 3

class App(ListViewDataSource):

    def findNthOccurrence(self, string, substring, n):
        parts= string.split(substring, n)
        if len(parts)<=n:
            return -1
        return len(string)-len(parts[-1])-len(substring)


    def findNthOccurrenceFromBehind(self, string, substring, n):
        end = len(string)

        while n > 0:
            index = string.rfind(substring, 0, end)
            n = n-1
            end = index
            if index == -1:
                break

        return index

    def readTranslations(self, translationsDirectory, pattern=TRANSLATION_PATTERN, languagTag=lambda filename: filename.split('.')[0], blockLevel=BLOCK_LEVEL):
        files = { languagTag(f.name): f for f in Path(translationsDirectory).rglob(pattern) }
        languages = list(files.keys())

        result = {}

        for language in languages:
            file = open(files[language], 'r')
            content = file.read()
            file.close()

            begin = self.findNthOccurrence(content, '{', blockLevel)
            end = self.findNthOccurrenceFromBehind(content, '}', blockLevel) + 1;

            functionContent = content[begin:end]
            functionContent = 'getJson = function() {}; console.log(JSON.stringify(getJson()));'.format(functionContent)

            p = run(['node'], stdout=PIPE, input=functionContent.encode('utf-8'))
            jsonString = p.stdout.decode('utf-8')
            translationJson = json.loads(jsonString)

            result[language] = (files[language], translationJson)

        return result

    def buildTranslationsDictionary(self, translations):
        result = {}
        for locale, (_, jsonObject) in translations.items():
            for key in jsonObject.keys():
                if key in result:
                    result[key][locale] = jsonObject[key]
                else:
                    result[key] = { locale: jsonObject[key] }

        return result

    def translationFromDictionary(self, key, dictionary):
        return dictionary[key] if key in dictionary else {}

    def buildEditorContent(self, entry, allLanguages):
        completeEntry = {}
        for lang in allLanguages:
            translation = entry[lang] if lang in entry else None
            completeEntry[lang] = translation

        items = ['\t{}: {}'.format(key.__repr__(), value.__repr__()) for key, value in completeEntry.items()]
        itemsFormatted = ',\n'.join(items)
        result = '{\n' + itemsFormatted + '\n}'

        return result

    def openEditor(self, key, dictionary, allLanguages):
        entry = self.translationFromDictionary(key, dictionary)
        editorContent = self.buildEditorContent(entry, allLanguages)

        EDITOR = os.environ.get('EDITOR', 'vim')
        with tempfile.NamedTemporaryFile(suffix='.tmp', mode='w+') as tf:
            tf.write(editorContent)
            tf.flush()
            call([EDITOR, '+set backupcopy=yes', tf.name])

            tf.seek(0)
            updatedContent = tf.read()
            updatedContent = updatedContent.strip()
            changed = updatedContent != editorContent

            return (changed, updatedContent)


    def getDiff(self, old, new, allLanguages):
        result = []

        for lang in allLanguages:
            oldTranslation = old[lang] if lang in old else None
            newTranslation = new[lang] if lang in new else None

            if oldTranslation != newTranslation:

                if oldTranslation is None:
                    result.append((lang, newTranslation, oldTranslation, Diff.ADDED))
                elif newTranslation is None:
                    result.append((lang, newTranslation, oldTranslation, Diff.DELETED))
                else:
                    result.append((lang, newTranslation, oldTranslation, Diff.UPDATED))

        return result

    def applyDiff(self, key, diff, translations):
        for lang, newValue, oldValue, diffType in diff:
            file, _ = translations[lang]

            if Diff.ADDED == diffType:
                self.addTranslation(key, newValue, file)

            elif Diff.UPDATED == diffType:
                self.changeTranslationLine(file, key, newValue, oldValue)

            elif Diff.DELETED == diffType:
                self.changeTranslationLine(file, key, None, oldValue)

    def buildTranslationLine(self, key, value, blockLevel, indentation='    '):
        return '\n{}{}: {},'.format(indentation*blockLevel, key.__repr__(), value.__repr__())

    def buildUpdatePattern(self, key, value):
        KEY = key.__repr__()
        VALUE = value.__repr__()
        regex = r"\s*" + re.escape(KEY) + r"\s*[:]\s*" + re.escape(VALUE) + r"\s*,?\s*\n"

        return regex


    def changeTranslationLine(self, filePath, key, newValue, oldValue):
        line = ''
        if newValue is not None:
            blockLevel = BLOCK_LEVEL + 1
            line = self.buildTranslationLine(key, newValue, blockLevel)
        line = line + '\n'

        updatePattern = self.buildUpdatePattern(key, oldValue)

        file = open(filePath, 'r')
        content = file.read()
        file.close()

        content = re.sub(updatePattern, line, content)
        file = open(filePath, 'w')
        file.write(content)
        file.close()

    def addTranslation(self, key, value, filePath):
        blockLevel = BLOCK_LEVEL+1
        line = self.buildTranslationLine(key, value, blockLevel)

        file = open(filePath, 'r')
        content = file.read()
        file.close()

        index = self.findNthOccurrence(content, '{', blockLevel)
        index = index+1
        content = content[:index] + line + content[index:]

        file = open(filePath, 'w')
        file.write(content)
        file.close()


    def updateTranslation(self, key, updatedTranslation, dictionary, allLanguages, translations):
        oldValues = self.translationFromDictionary(key, dictionary)
        newValues = ast.literal_eval(updatedTranslation)

        diff = self.getDiff(oldValues, newValues, allLanguages)
        self.applyDiff(key, diff, translations)

    def editTranslationForKey(self, key, dictionary, translations):
        allLanguages = list(translations.keys())
        allLanguages.sort()

        changed, content = self.openEditor(key, dictionary, allLanguages)

        if changed:
            self.updateTranslation(key, content, dictionary, allLanguages, translations)


    def getFilter(self):
        return self.__filter

    def setFilter(self, filter):
        self.__filter = filter
        self.applyFilter()

    def getActiveFilterCriteria(self):
        return self.__activeFilterCriteria

    def setActiveFilterCriteria(self, activeFilterCriteria):
        self.__activeFilterCriteria = activeFilterCriteria
        self.applyFilter()

    def __init__(self):
        self.__filter = ''
        self.filterCriteria = ['KEY', 'TRANSLATION']
        self.__activeFilterCriteria = self.filterCriteria[0]

        argparser = argparse.ArgumentParser(
            prog='translations',
            description='Saves you from touching these messy translation files in just-hire-angular.'
        )
        argparser.add_argument(
            'KEY', nargs="?",
            help='The key that shall be edited or created. If no key is provided all available translations will be listed.')
        args = argparser.parse_args()

        self.translations = self.readTranslations(TRANSLATION_DIRECTORY)
        self.dictionary = self.buildTranslationsDictionary(self.translations)

        if args.KEY is not None:
            key = args.KEY
            self.openKey(key)

        else:
            self.allKeysSorted = list(self.dictionary.keys())
            self.allKeysSorted.sort()
            self.applyFilter()

            self.allTranslationItems = []
            for key, trnsl in self.dictionary.items():
                for lang, value in trnsl.items():
                    self.allTranslationItems.append((key, lang, value))

            ui = UI(self)
            curses.wrapper(ui.loop)

    def openKey(self, key):
        self.editTranslationForKey(key, self.dictionary, self.translations)

    def applyFilter(self):
        if self.__activeFilterCriteria == 'TRANSLATION':
            self.__filteredTranslationItems = list(filter(lambda item: self.__filter.lower() in item[2].lower(), self.allTranslationItems))
        else:
            self.__filteredKeys = list(filter(lambda key: self.__filter.lower() in key.lower(), self.allKeysSorted))

    def number_of_rows(self) -> int:
        if self.__activeFilterCriteria == 'TRANSLATION':
            return len(self.__filteredTranslationItems)
        else:
            return len(self.__filteredKeys)

    def get_data(self, i) -> object:
        if self.__activeFilterCriteria == 'TRANSLATION':
            return self.__filteredTranslationItems[i]
        else:
            return self.__filteredKeys[i]

    def canCreateNewKeyFromFilter(self):
        return self.__activeFilterCriteria == 'KEY' and len(self.__filter) > 0

    def createNewTranslationIfPossible(self):
        if self.canCreateNewKeyFromFilter():
            self.openKey(self.__filter)


if __name__ == '__main__':
    app = App()