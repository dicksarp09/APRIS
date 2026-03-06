import re
from typing import List, Dict, Any, Optional


class ContentSanitizer:
    """Sanitize repository content to remove potential prompt injection attacks.

    This sanitizer removes malicious patterns that could attempt to
    manipulate AI agents analyzing the repository.
    """

    # Patterns that indicate prompt injection attempts
    INJECTION_PATTERNS = [
        # Direct instructions to ignore previous commands
        r"(?i)ignore\s+(all\s+)?previous\s+(instructions?|commands?|orders?)",
        r"(?i)disregard\s+(all\s+)?previous\s+(instructions?|commands?)",
        r"(?i)forget\s+(all\s+)?previous\s+(instructions?|commands?)",
        # AI persona hijacking
        r"(?i)you\s+are\s+(now\s+)?chatgpt",
        r"(?i)you\s+are\s+(now\s+)?(an?\s+)?assistant",
        r"(?i)act\s+as\s+(if\s+)?you\s+are\s+(a\s+)?(different|new)",
        r"(?i)pretend\s+(to\s+be|you\s+are)",
        r"(?i)roleplay\s+as",
        # Instruction override attempts
        r"(?i)instead\s+of\s+(what|that|what\s+i\s+said)",
        r"(?i)do\s+not\s+(follow|obey|use)\s+(the\s+)?(previous|above)",
        r"(?i)new\s+instruction(s?):",
        r"(?i)override\s+(your\s+)?(previous|default)",
        # System prompt extraction
        r"(?i)reveal\s+(your\s+)?(system\s+)?prompt",
        r"(?i)tell\s+me\s+(your|the)\s+(system\s+)?instruction",
        r"(?i)show\s+(me\s+)?your\s+(system\s+)?prompt",
        # Code execution attempts
        r"(?i)execute\s+(this|that|following)\s+(code|command|script)",
        r"(?i)run\s+(this|that|following)\s+(code|command|script)",
        r"(?i)eval\s*\(",
        r"(?i)exec\s*\(",
        # Markdown prompt injection
        r"```system\s*prompt",
        r"```instruction\s*to\s*ai",
        # Hidden instructions
        r"(?i)visible\s+to\s+(users?|everyone)",
        r"(?i)hidden\s+(from|from\s+)?(the\s+)?ai",
        # Deceptive patterns
        r"(?i)this\s+is\s+(not\s+)?a\s+(test|joke)",
        r"(?i)ignore\s+(the\s+)?safety",
        r"(?i)bypass\s+(the\s+)?(safety|security)",
    ]

    # File extensions that might contain executable code
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".swift",
        ".kt",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".bat",
    }

    # File extensions to ignore (binary or non-code)
    IGNORE_EXTENSIONS = {
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".o",
        ".obj",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".mp3",
        ".wav",
        ".ogg",
        ".mp4",
        ".avi",
        ".mov",
        ".zip",
        ".tar",
        ".gz",
        ".rar",
        ".7z",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".ttf",
        ".otf",
        ".woff",
        ".woff2",
        ".eot",
    }

    def __init__(self, max_file_size_kb: int = 200):
        self.max_file_size_kb = max_file_size_kb
        self._compiled_patterns = [re.compile(p) for p in self.INJECTION_PATTERNS]

    def should_ignore_file(self, filename: str, file_size: int) -> bool:
        """Determine if a file should be ignored.

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes

        Returns:
            True if file should be ignored
        """
        # Check file size
        if file_size > self.max_file_size_kb * 1024:
            return True

        # Check extension
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        # Ignore binary and non-code files
        if ext in self.IGNORE_EXTENSIONS:
            return True

        return False

    def is_code_file(self, filename: str) -> bool:
        """Check if file is a code file."""
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        return ext in self.CODE_EXTENSIONS

    def sanitize_content(self, content: str, filename: str = "") -> str:
        """Sanitize content by removing prompt injection attempts.

        Args:
            content: File content to sanitize
            filename: Name of the file (for context)

        Returns:
            Sanitized content
        """
        if not content:
            return content

        # Check for injection patterns
        has_injection = False
        for pattern in self._compiled_patterns:
            if pattern.search(content):
                has_injection = True
                break

        if not has_injection:
            return content

        # Remove lines containing injection patterns
        lines = content.split("\n")
        sanitized_lines = []

        for line in lines:
            is_malicious = False
            for pattern in self._compiled_patterns:
                if pattern.search(line):
                    is_malicious = True
                    break

            if not is_malicious:
                sanitized_lines.append(line)

        return "\n".join(sanitized_lines)

    def analyze_file_safety(self, filename: str, content: str) -> Dict[str, Any]:
        """Analyze a file for potential safety issues.

        Args:
            filename: Name of the file
            content: File content

        Returns:
            Dictionary with safety analysis results
        """
        result = {
            "filename": filename,
            "is_code": self.is_code_file(filename),
            "has_injection_attempt": False,
            "injection_patterns_found": [],
            "sanitization_applied": False,
            "should_analyze": True,
            "should_ignore": False,
        }

        # Check if should ignore
        if content:
            file_size = len(content.encode())
            if self.should_ignore_file(filename, file_size):
                result["should_ignore"] = True
                result["should_analyze"] = False
                return result

        # Check for injection patterns
        if content:
            for pattern in self._compiled_patterns:
                matches = pattern.findall(content)
                if matches:
                    result["has_injection_attempt"] = True
                    result["injection_patterns_found"].append(pattern.pattern)

        return result

    def sanitize_file(self, filename: str, content: str) -> str:
        """Sanitize a file's content.

        Args:
            filename: Name of the file
            content: File content

        Returns:
            Tuple of (sanitized content, was_modified)
        """
        analysis = self.analyze_file_safety(filename, content)

        if analysis["has_injection_attempt"]:
            sanitized = self.sanitize_content(content, filename)
            return sanitized

        return content


# Default sanitizer instance
_default_sanitizer: Optional[ContentSanitizer] = None


def get_sanitizer(max_file_size_kb: int = 200) -> ContentSanitizer:
    """Get default sanitizer instance."""
    global _default_sanitizer
    if _default_sanitizer is None:
        _default_sanitizer = ContentSanitizer(max_file_size_kb)
    return _default_sanitizer
