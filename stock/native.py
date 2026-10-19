"""Terminal defaults are colors, not an approximation of a dark theme."""
NATIVE_CSS = '''
Screen, VerticalScroll, Static, TextArea, TextArea:focus {
    background: ansi_default;
    color: ansi_default;
    background-tint: transparent;
    text-opacity: 100%;
}
TextArea { scrollbar-size: 0 0; }
TextArea .text-area--cursor-line, TextArea .text-area--gutter,
TextArea .text-area--cursor-gutter {
    background: ansi_default;
    color: ansi_default;
}
'''
