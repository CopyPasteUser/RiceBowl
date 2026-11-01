---
version: 1.0
name: "MacBar"
description: "A quiet, fast macOS-inspired status strip for Linux Mint XFCE/X11."
colors:
  accent: "#0a84ff"
  dark-surface: "rgba(20,22,29,.91)"
  dark-text: "#f6f6fa"
  dark-hover: "rgba(255,255,255,.13)"
  dark-divider: "rgba(255,255,255,.16)"
  light-surface: "rgba(245,246,249,.93)"
  light-text: "#1f2430"
  light-hover: "rgba(0,0,0,.07)"
  light-divider: "rgba(0,0,0,.12)"
typography:
  interface:
    fontFamily: "Inter, sans-serif"
    fontSize: "11px"
rounded:
  control: "5px"
spacing:
  icon-gap: "4px"
  button-x: "7px"
components:
  topbar: {}
  icon-button: {}
  status-indicator: {}
---

# MacBar Design System

## Overview

An X11 desktop menu strip inspired by macOS's top bar, paired with the user's
existing monochrome Linux MacMenu icon, WhiteSur icon theme, Plank dock and separate
Control Center. It is a functional system surface, not a floating dashboard.
It is deliberately still at rest; its signature is the familiar user icon at
the far left, blank breathing room, and a compact set of true system
indicators on the right.

The target user is a Linux Mint XFCE power user on a small laptop. All
accessibility descriptions and clock abbreviations are in English.
There are no transitions or scroll containers in the bar. Do not mimic the
heavy blur, giant rounded cards, gradient backgrounds or large spacing of a
web SaaS dashboard.

Runtime GTK CSS is built in `macbar.py` from `THEMES`, which is canonical;
this file mirrors its palette. The configured `height` defaults to 30px and
can range from 26 to 48px. There is no second generated-token layer.

## Colors

Dark mode: `dark-surface`, `dark-text`, `dark-hover`, `dark-divider`.
Light mode: matching `light-*` roles. The accent `#0a84ff` is used sparingly,
only for keyboard focus and Control Center intent. Contrast derives primarily
from foreground against the semi-opaque surface. Compositor transparency must
not obscure readability.

## Typography

System sans-serif 12px, weight 500 for the clock. The clock uses local time,
formatted in English, and shortens on narrow screens.

## Layout

A single unbroken bar, 30px tall, full width of the primary monitor, at the
top edge. The left cluster has MacMenu only; an expanding
spacer pushes the network/audio/battery/control center/clock group right.
There is no tasklist because Plank already provides running-app access.
Read-only status indicators may be hidden only when the hardware is absent
(battery). Battery percentage is hidden on narrow screens. Only MacMenu and
Control Center are clickable.

## Elevation & Depth

One translucent background with a 1px bottom divider. No shadows, full blur,
shader, animated background, popovers or overlay adornments.

## Shapes

Low-radius 5px click targets for the two launchers rather than high-radius pills.
Read-only indicators have no clickable affordance. Icon size 16–19px.
Transparent resting launcher buttons; a pale hover fill and a blue focus ring.

## Components

`topbar` is a GTK dock window with an X11 EWMH strut, keeping maximized windows
below it. `icon-button` uses native Gtk.Button semantics for MacMenu and Control
Center. `status-indicator` is a non-clickable Gtk.Box with English accessible
text and no popup. Launcher errors are logged and shown by a red icon rather
than a floating tooltip.

## Do's and Don'ts

- Do prefer GTK/GLib event signals for status changes over shell loops.
- Do keep every action keyboard accessible and independently testable.
- Don't add a task list, permanent notifications, or redundant Control Center UI.
- Don't promise a third-party system tray or universal global application menu
  until supported and tested explicitly.
