from gupy.geometry import Padding
from gupy.view import BackgroundView, Label, HBox, ListView
from gupy.screen import ConstrainedBasedScreen
from lib import colorpairs, keys, legends
from pathlib import Path
import curses


class UI:

    def __init__(self, filterCriteria):
        self.isFiltering = False
        self.filter = ''
        self.filterCriteria = filterCriteria
        self.activeFilterCriteria = filterCriteria[0]

    def setupColors(self):
        curses.curs_set(0)

        curses.init_pair(colorpairs.KEY, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(colorpairs.DESCRIPTION, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(colorpairs.PATTERN, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
        curses.init_pair(colorpairs.SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)

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

        filterCriteriaLabel = Label('[KEY]=')
        filterCriteriaLabel.attributes.append(curses.color_pair(colorpairs.FILTER_CRITERIA))
        filterCriteriaLabel.attributes.append(curses.A_BOLD)

        filterLabel = Label('foobar')
        filterLabel.attributes.append(curses.color_pair(colorpairs.FILTER_VALUE))

        filterHBox = HBox();
        filterHBox.add_view(filterCriteriaLabel, Padding(0, 0, 0, 0))
        filterHBox.add_view(filterLabel, Padding(0, 0, 0, 0))

        screen.add_view(filterHBox, lambda w, h, v: (0, 0, w, 1))

        return (filterBackground, filterHBox, filterCriteriaLabel, filterLabel)

    def updateFilterBox(self, filterElements):
        _, _, filterCriteriaLabel, filterLabel = filterElements

        filterLabel.text = self.filter

        filterCriteria = self.activeFilterCriteria + '='
        if len(self.filter) > 0:
            filterCriteriaLabel.text = filterCriteria
        else:
            filterCriteriaLabel.text = filterCriteria if self.isFiltering else ''

        filterCriteriaLabel.attributes.clear()
        filterCriteriaLabel.attributes.append(curses.A_BOLD)
        color = curses.color_pair(colorpairs.FILTER_CRITERIA_EDITING) if self.isFiltering else curses.color_pair(colorpairs.FILTER_CRITERIA)
        filterCriteriaLabel.attributes.append(color)

    def selectPreviousFilterCriteria(self):
        index = self.filterCriteria.index(self.activeFilterCriteria)
        index = index-1
        if index < 0:
            index = len(self.filterCriteria)-1
        self.activeFilterCriteria = self.filterCriteria[index]

    def selectNextFilterCriteria(self):
        index = self.filterCriteria.index(self.activeFilterCriteria)
        index = index+1
        if index >= len(self.filterCriteria):
            index = 0
        self.activeFilterCriteria = self.filterCriteria[index]

    def loop(self, stdscr):

        self.setupColors()

        screen = ConstrainedBasedScreen(stdscr)
        legendElements = self.addLegend(screen, legends.MAIN)
        filterElements = self.addFilterBox(screen)

        while 1:
            self.updateFilterBox(filterElements)

            screen.render()

            key = stdscr.getch()
            if self.isFiltering:
                if key == keys.ESCAPE:
                    self.isFiltering = False
                    screen.remove_views(list(legendElements))
                    legendElements = self.addLegend(screen, legends.MAIN)
                    self.filter = ''

                elif key == keys.ENTER:
                    self.isFiltering = False
                    screen.remove_views(list(legendElements))
                    legendElements = self.addLegend(screen, legends.MAIN)

                elif key == keys.BACKSPACE:
                    self.filter = self.filter[:-1]

                elif key == keys.UP:
                    self.selectPreviousFilterCriteria()

                elif key == keys.DOWN:
                    self.selectNextFilterCriteria()

                elif key in [keys.LEFT, keys.RIGHT]:
                    pass

                else:
                    character = chr(key)
                    self.filter = self.filter + character

            else:
                if key == keys.F:
                    self.isFiltering = True
                    screen.remove_views(list(legendElements))
                    legendElements = self.addLegend(screen, legends.FILTER)

                if key == keys.C:
                    self.filter = ''

                if key == keys.Q:
                    exit(0)