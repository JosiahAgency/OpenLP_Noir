# -*- coding: utf-8 -*-

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
"""
The :mod:`~openlp.plugins.alerts.lib.presets` module defines the alert priority
levels and the per-priority style presets (typography, background, position,
animation and behaviour). Each priority owns one fully editable preset; an
alert only carries its text and priority, and the preset supplies the look.
"""
import copy
import json
from enum import IntEnum

from openlp.core.common.i18n import translate


class AlertPriority(IntEnum):
    """
    The priority of an alert. The priority selects the style preset and the
    queueing behaviour.
    """
    Info = 0
    Notice = 1
    Important = 2
    Critical = 3

    @property
    def key(self):
        """The settings/JSON key for this priority."""
        return PRIORITY_KEYS[self.value]

    @staticmethod
    def display_names():
        """Translated display names, indexed by priority value."""
        return [
            translate('AlertsPlugin', 'Info'),
            translate('AlertsPlugin', 'Notice'),
            translate('AlertsPlugin', 'Important'),
            translate('AlertsPlugin', 'Critical'),
        ]


PRIORITY_KEYS = ['info', 'notice', 'important', 'critical']

# How each priority behaves when it meets the queue:
#   queue   - first in, first out
#   front   - jumps ahead of any queued (but not showing) alerts
#   preempt - interrupts the alert currently on screen (which is re-queued)
PRIORITY_BEHAVIOUR = {
    AlertPriority.Info: 'queue',
    AlertPriority.Notice: 'queue',
    AlertPriority.Important: 'front',
    AlertPriority.Critical: 'preempt',
}

ALERT_TYPES = ['banner', 'toast', 'lowerThird', 'centerOverlay', 'fullscreen']
ZONES_H = ['left', 'center', 'right']
ZONES_V = ['top', 'middle', 'bottom']
BACKGROUND_STYLES = ['solid', 'gradient', 'glass', 'semiTransparent', 'none']
SHAPES = ['fullWidth', 'rounded', 'pill', 'card']
ANIMATIONS_IN = ['none', 'fade', 'slideDown', 'slideUp', 'slideLeft', 'slideRight', 'zoom', 'bounce', 'flip']
ANIMATIONS_OUT = ['none', 'fade', 'slideDown', 'slideUp', 'slideLeft', 'slideRight', 'zoom', 'flip']
EMPHASIS_EFFECTS = ['none', 'pulse', 'flash', 'shake']
ICONS = ['auto', 'none', 'info', 'bell', 'warning', 'critical', 'megaphone', 'clock', 'heart']

# The base preset every priority starts from. All keys are camelCase because
# the resolved preset is passed straight to the display's Javascript.
_BASE_PRESET = {
    'alertType': 'banner',
    'zoneH': 'center',
    'zoneV': 'top',
    'offsetX': 0,           # percent of screen width, -50 .. 50
    'offsetY': 0,           # percent of screen height, -50 .. 50
    'fontFace': 'Lato',
    'fontSize': 40,         # pt
    'fontColor': '#FFFFFF',
    'fontWeight': 700,      # CSS weight, 100 .. 900 (Lato's cuts: 300/400/700/900)
    'letterSpacing': 0.0,   # px
    'lineSpacing': 1.2,     # multiplier
    'textOpacity': 100,     # percent
    'textShadowEnabled': True,
    'textShadowColor': '#000000',
    'textShadowX': 0,
    'textShadowY': 2,
    'textShadowBlur': 8,
    'outlineEnabled': False,
    'outlineColor': '#000000',
    'outlineWidth': 2,      # px
    'glowEnabled': False,
    'glowColor': '#4D9FFF',
    'glowRadius': 16,       # px
    'backgroundStyle': 'solid',
    'backgroundColor': '#1B1F26',
    'backgroundColor2': '#0E1014',
    'gradientAngle': 135,   # degrees
    'backgroundOpacity': 100,   # percent
    'backgroundBlur': 14,   # px, backdrop blur used by the glass style
    'shape': 'fullWidth',
    'cornerRadius': 18,     # px
    'paddingX': 40,         # px
    'paddingY': 18,         # px
    'marginX': 32,          # px, distance from the screen edge (non full-width shapes)
    'marginY': 32,          # px
    'iconEnabled': True,
    'icon': 'auto',
    'animationIn': 'slideDown',
    'animationOut': 'fade',
    'animationSpeed': 400,  # ms
    'emphasis': 'none',
    'scroll': False,
    'timeout': 8,           # seconds on screen
    'repeat': 1,            # number of passes when scrolling
}


def _preset(**overrides):
    preset = dict(_BASE_PRESET)
    preset.update(overrides)
    return preset


# The factory look of each priority. Info is a quiet corner toast, Notice a
# top banner, Important a lower third, Critical a fullscreen takeover.
DEFAULT_PRESETS = {
    'info': _preset(
        alertType='toast',
        zoneH='right',
        zoneV='bottom',
        fontSize=24,
        fontWeight=400,
        backgroundStyle='glass',
        backgroundColor='#1B1F26',
        backgroundOpacity=82,
        shape='card',
        cornerRadius=16,
        paddingX=28,
        paddingY=16,
        animationIn='slideUp',
        animationOut='fade',
        timeout=6,
    ),
    'notice': _preset(
        alertType='banner',
        zoneH='center',
        zoneV='top',
        fontSize=32,
        backgroundStyle='glass',
        backgroundColor='#14273D',
        backgroundOpacity=88,
        shape='fullWidth',
        animationIn='slideDown',
        animationOut='slideUp',
        timeout=8,
    ),
    'important': _preset(
        alertType='lowerThird',
        zoneH='center',
        zoneV='bottom',
        fontSize=38,
        fontWeight=700,
        fontColor='#141414',
        textShadowEnabled=False,
        backgroundStyle='gradient',
        backgroundColor='#E8B14C',
        backgroundColor2='#D9822B',
        gradientAngle=120,
        shape='rounded',
        cornerRadius=14,
        marginY=48,
        animationIn='slideLeft',
        animationOut='fade',
        emphasis='pulse',
        timeout=12,
    ),
    'critical': _preset(
        alertType='fullscreen',
        zoneH='center',
        zoneV='middle',
        fontSize=56,
        fontWeight=900,
        letterSpacing=1.0,
        backgroundStyle='gradient',
        backgroundColor='#C13A30',
        backgroundColor2='#5E1712',
        gradientAngle=160,
        backgroundOpacity=96,
        shape='fullWidth',
        animationIn='zoom',
        animationOut='fade',
        emphasis='flash',
        timeout=20,
    ),
}


def get_alert_presets(settings):
    """
    Return the current presets for all four priorities: the built-in defaults
    deep-merged with any user overrides stored in the ``alerts/presets``
    setting (a JSON object keyed by priority).

    :param settings: A Settings instance.
    :return: dict of priority key -> full preset dict
    """
    presets = {key: dict(DEFAULT_PRESETS[key]) for key in PRIORITY_KEYS}
    saved = settings.value('alerts/presets')
    if saved:
        # Settings may hand back the JSON string, or an already-decoded dict
        if isinstance(saved, dict):
            overrides = saved
        else:
            try:
                overrides = json.loads(saved)
            except (TypeError, ValueError):
                return presets
        if isinstance(overrides, dict):
            for key in PRIORITY_KEYS:
                priority_overrides = overrides.get(key)
                if isinstance(priority_overrides, dict):
                    # Only accept known keys so stale/bad entries can't leak
                    # into the display Javascript.
                    for name, value in priority_overrides.items():
                        if name in _BASE_PRESET:
                            presets[key][name] = value
    return presets


def save_alert_presets(settings, presets):
    """
    Persist the presets. Only the values differing from the built-in defaults
    are stored, so future default improvements reach untouched settings.

    :param settings: A Settings instance.
    :param presets: dict of priority key -> full preset dict
    """
    overrides = {}
    for key in PRIORITY_KEYS:
        defaults = DEFAULT_PRESETS[key]
        changed = {name: value for name, value in presets.get(key, {}).items()
                   if name in _BASE_PRESET and value != defaults[name]}
        if changed:
            overrides[key] = changed
    settings.setValue('alerts/presets', json.dumps(overrides) if overrides else '')


def resolve_alert_settings(settings, priority):
    """
    Build the settings dict handed to the display Javascript for an alert of
    the given priority.

    :param settings: A Settings instance.
    :param priority: An AlertPriority (or int priority value).
    :return: The preset dict, plus the priority key under ``priority``.
    """
    priority = AlertPriority(priority)
    preset = get_alert_presets(settings)[priority.key]
    preset['priority'] = priority.key
    return preset


def new_template_style(settings, priority):
    """
    A starting style for a brand-new alert template: a standalone copy of the
    given priority's current global preset, so editing it afterwards cannot
    affect (or be affected by) that priority's default.

    :param settings: A Settings instance.
    :param priority: An AlertPriority (or int priority value) to start from.
    :return: A fully independent preset dict.
    """
    priority = AlertPriority(priority)
    style = copy.deepcopy(get_alert_presets(settings)[priority.key])
    style['priority'] = priority.key
    return style


def resolve_template_style(alert_item, settings):
    """
    Build the settings dict handed to the display Javascript for a saved
    alert template. Templates carry their own style; alerts saved before
    per-template styling existed (or otherwise missing a style) fall back to
    their priority's current global preset.

    :param alert_item: An AlertItem.
    :param settings: A Settings instance.
    :return: The template's style dict, plus the priority key under ``priority``.
    """
    priority = AlertPriority(alert_item.priority or 0)
    style = None
    if alert_item.style:
        try:
            decoded = json.loads(alert_item.style)
        except (TypeError, ValueError):
            decoded = None
        if isinstance(decoded, dict):
            # Start from the base preset so a template saved before a new
            # style field was introduced still gets a sane value for it, then
            # only accept known keys so stale/bad entries can't leak into the
            # display Javascript.
            style = dict(_BASE_PRESET)
            for name, value in decoded.items():
                if name in _BASE_PRESET:
                    style[name] = value
    if style is None:
        return resolve_alert_settings(settings, priority)
    style['priority'] = priority.key
    return style
