from gupy.geometry import Padding
from gupy.view import BackgroundView, Label, HBox, ListView, ListViewDelegate, View
from gupy.screen import ConstrainedBasedScreen
from lib import colorpairs, keys, legends
from pathlib import Path
import curses


class UI(ListViewDelegate):

    def __init__(self, app):
        self.app = app

    def setupColors(self):
        curses.curs_set(0)

        curses.init_pair(colorpairs.KEY, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(colorpairs.DESCRIPTION, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(colorpairs.PATTERN, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
        curses.init_pair(colorpairs.SELECTED, curses.COLOR_BLACK, curses.COLOR_GREEN)

        curses.init_pair(colorpairs.ADDED, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.DELETED, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.MODIFIED, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.MOVED, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.UNTRACKED, curses.COLOR_CYAN, curses.COLOR_BLACK)

        curses.init_pair(colorpairs.STAGED, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.CONFIRMATION, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(colorpairs.CONFIRMATION_SELECTION, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.init_pair(colorpairs.FILTER_CRITERIA, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(colorpairs.FILTER_CRITERIA_EDITING, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
        curses.init_pair(colorpairs.FILTER_VALUE, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.init_pair(colorpairs.LANG, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    def addLegend(self, screen, legendItems):

        moreLabel = Label('')
        def setMoreLabel(clipped):
            moreLabel.text = '...' if clipped else ''

        legendHBox = HBox()
        legendHBox.clipping_callback = setMoreLabel

        for key, description in legendItems:
            keyLabel = Label(key)
            keyLabel.attributes.append(curses.color_pair(colorpairs.KEY))
            legendHBox.add_view(keyLabel, Padding(2, 0, 0, 0))

            descriptionLabel = Label(description)
            descriptionLabel.attributes.append(curses.color_pair(colorpairs.DESCRIPTION))
            legendHBox.add_view(descriptionLabel, Padding(0, 0, 0, 0))

        screen.add_view(legendHBox, lambda w, h, v: (0, h-1, w-moreLabel.required_size().width, 1))
        screen.add_view(moreLabel, lambda w, h, v: (w-v.required_size().width-1, h-1, v.required_size().width, 1))

        return (legendHBox, moreLabel)

    def addFilterBox(self, screen):

        filterBackground = BackgroundView(curses.color_pair(colorpairs.FILTER_VALUE))
        screen.add_view(filterBackground, lambda w, h, v: (0, 0, w, 1))

        filterCriteriaLabel = Label('sss')
        filterCriteriaLabel.attributes.append(curses.color_pair(colorpairs.FILTER_CRITERIA))
        filterCriteriaLabel.attributes.append(curses.A_BOLD)

        filterLabel = Label('...')
        filterLabel.attributes.append(curses.color_pair(colorpairs.FILTER_VALUE))

        filterHBox = HBox();
        filterHBox.add_view(filterCriteriaLabel, Padding(0, 0, 0, 0))
        filterHBox.add_view(filterLabel, Padding(0, 0, 0, 0))

        screen.add_view(filterHBox, lambda w, h, v: (0, 0, w, 1))

        return (filterBackground, filterHBox, filterCriteriaLabel, filterLabel)

    def updateFilterBox(self, filterElements):
        _, _, filterCriteriaLabel, filterLabel = filterElements

        filterLabel.text = self.app.getFilter()

        filterCriteria = self.app.getActiveFilterCriteria() + '='
        if len(self.app.getFilter()) > 0:
            filterCriteriaLabel.text = filterCriteria
        else:
            filterCriteriaLabel.text = filterCriteria if self.isFiltering else ''

        filterCriteriaLabel.attributes.clear()
        filterCriteriaLabel.attributes.append(curses.A_BOLD)
        color = curses.color_pair(colorpairs.FILTER_CRITERIA_EDITING) if self.isFiltering else curses.color_pair(colorpairs.FILTER_CRITERIA)
        filterCriteriaLabel.attributes.append(color)

    def selectPreviousFilterCriteria(self):
        index = self.app.filterCriteria.index(self.app.getActiveFilterCriteria())
        index = index-1
        if index < 0:
            index = len(self.app.filterCriteria)-1
        self.app.setActiveFilterCriteria(self.app.filterCriteria[index])

    def selectNextFilterCriteria(self):
        index = self.app.filterCriteria.index(self.app.getActiveFilterCriteria())
        index = index+1
        if index >= len(self.app.filterCriteria):
            index = 0
        self.app.setActiveFilterCriteria(self.app.filterCriteria[index])

    def addListView(self, screen):
        listView = ListView(self, self.app)
        screen.add_view(listView, lambda w, h, v: (0, 1, w, h-2))

        return listView

    def build_row(self, i, data, is_selected, width) -> View:
        rowHBox = HBox()

        if isinstance(data, tuple):
            key, lang, value = data
            langLabel = Label('[' + lang + ']')
            langLabel.attributes.append(curses.color_pair(colorpairs.LANG))

            valueLabel = Label(value.__repr__())
            valueLabel.attributes.append(curses.A_BOLD)

            keyLabel = Label('(' + key + ')')

            rowHBox.add_view(langLabel, Padding(1, 0, 0, 1))
            rowHBox.add_view(valueLabel, Padding(1, 0, 0, 1))
            rowHBox.add_view(keyLabel, Padding(2, 0, 0, 0))
        else:
            keyLabel = Label(data)
            rowHBox.add_view(keyLabel, Padding(1, 0, 0, 0))

        result = rowHBox
        if is_selected:
            result = BackgroundView(curses.color_pair(colorpairs.SELECTED))
            result.add_view(rowHBox)
            for label in rowHBox.get_elements():
                label.attributes.append(curses.color_pair(colorpairs.SELECTED))

        return result

    def loop(self, stdscr):

        self.setupColors()

        screen = ConstrainedBasedScreen(stdscr)
        legendElements = self.addLegend(screen, legends.MAIN)
        filterElements = self.addFilterBox(screen)
        listView = self.addListView(screen)

        self.isFiltering = False

        while 1:
            self.updateFilterBox(filterElements)

            screen.render()

            key = stdscr.getch()
            if self.isFiltering:
                if key == keys.ESCAPE:
                    self.isFiltering = False
                    screen.remove_views(list(legendElements))
                    legendElements = self.addLegend(screen, legends.MAIN)
                    self.app.setFilter('')
                elif key == keys.ENTER:
                    self.isFiltering = False
                    screen.remove_views(list(legendElements))
                    legendElements = self.addLegend(screen, legends.MAIN)

                elif key == keys.BACKSPACE:
                    self.app.setFilter(self.app.getFilter()[:-1])

                elif key == keys.UP:
                    self.selectPreviousFilterCriteria()

                elif key == keys.DOWN:
                    self.selectNextFilterCriteria()

                elif key in [keys.LEFT, keys.RIGHT]:
                    pass

                else:
                    character = chr(key)
                    self.app.setFilter(self.app.getFilter() + character)

            else:
                if key == keys.F:
                    self.isFiltering = True
                    screen.remove_views(list(legendElements))
                    legendElements = self.addLegend(screen, legends.FILTER)

                if key == keys.UP:
                    listView.select_previous()

                if key == keys.DOWN:
                    listView.select_next()

                if key == keys.C:
                    self.app.setFilter('')

                if key == keys.ENTER:
                    data = self.app.get_data(listView.get_selected_row_index())
                    if isinstance(data, tuple):
                        key, _, _ = data
                        self.app.openKey(key)
                        exit(0)

                    else:
                        self.app.openKey(data)
                        exit(0)

                if key == keys.Q:
                    exit(0)