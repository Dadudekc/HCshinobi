"""Dream.OS Theme System."""

class DreamTheme:
    """Dream.OS color and style constants."""
    
    # Primary colors
    PRIMARY = "#007AFF"
    PRIMARY_VARIANT = "#0055FF"
    PRIMARY_DARK = "#005AC1"
    
    # Secondary colors
    SECONDARY = "#6C757D"
    SECONDARY_VARIANT = "#495057"
    
    # Background colors
    BACKGROUND = "#1E1E1E"
    SURFACE = "#252526"
    SURFACE_VARIANT = "#2D2D2D"
    
    # Text colors
    TEXT = "#FFFFFF"
    TEXT_SECONDARY = "#B2B2B2"
    TEXT_DISABLED = "#6C757D"
    
    # Status colors
    SUCCESS = "#28A745"
    ERROR = "#DC3545"
    WARNING = "#FFC107"
    INFO = "#17A2B8"
    
    # Accent colors
    ACCENT_PURPLE = "#6F42C1"
    ACCENT_PINK = "#E83E8C"
    ACCENT_ORANGE = "#FD7E14"
    ACCENT_TEAL = "#20C997"
    
    # Border colors
    BORDER = "#323232"
    BORDER_LIGHT = "#404040"
    
    # Shadow colors
    SHADOW = "rgba(0, 0, 0, 0.2)"
    SHADOW_DARK = "rgba(0, 0, 0, 0.4)"
    
    @classmethod
    def get_button_style(cls, variant="primary"):
        """Get button style based on variant."""
        variants = {
            "primary": (cls.PRIMARY, cls.PRIMARY_VARIANT),
            "secondary": (cls.SECONDARY, cls.SECONDARY_VARIANT),
            "success": (cls.SUCCESS, "#218838"),
            "error": (cls.ERROR, "#C82333"),
            "warning": (cls.WARNING, "#E0A800"),
            "info": (cls.INFO, "#138496")
        }
        color, hover = variants.get(variant, variants["primary"])
        
        return f"""
            background-color: {color};
            color: {cls.TEXT};
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        """
    
    @classmethod
    def get_input_style(cls):
        """Get style for input elements."""
        return f"""
            background-color: {cls.SURFACE};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
            padding: 8px;
        """
    
    @classmethod
    def get_card_style(cls):
        """Get style for card elements."""
        return f"""
            background-color: {cls.SURFACE};
            border-radius: 8px;
            padding: 16px;
            margin: 8px;
            box-shadow: 0 2px 4px {cls.SHADOW};
        """
    
    @classmethod
    def get_header_style(cls):
        """Get style for header elements."""
        return f"""
            color: {cls.TEXT};
            font-size: 24px;
            font-weight: bold;
            margin: 16px 0;
        """
    
    @classmethod
    def get_tab_style(cls):
        """Get style for tab elements."""
        return f"""
            QTabBar::tab {{
                background-color: {cls.SURFACE};
                color: {cls.TEXT_SECONDARY};
                border: none;
                padding: 8px 16px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT};
            }}
            QTabBar::tab:hover {{
                background-color: {cls.PRIMARY_VARIANT};
            }}
        """ 