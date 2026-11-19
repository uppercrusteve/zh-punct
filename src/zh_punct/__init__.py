"""zh-punct：中文排版体检。

只查机器判得准的形态问题：全半角混用、成对符号不闭合、重复标点、省略号与破折号写法。
标点用法争议（该不该加逗号、语气）不查。
"""

from __future__ import annotations

__version__ = "0.1.0"

from .rules import RULES, Diagnostic, apply_fixes, check_text

__all__ = ["RULES", "Diagnostic", "__version__", "apply_fixes", "check_text"]
