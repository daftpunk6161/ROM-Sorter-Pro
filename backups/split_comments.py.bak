#!/usr/bin/env python3
"""
Helper script for splitting long comment lines in source code.
The script reads a source file, looks for long lines in comments,
and splits them into multiple lines.
"""

import sys
import re

def split_long_comment_lines(file_path, max_line_length=79):
    """
    Splits long comment lines in a file.

    Args:
        file_path: Path to the file to process
        max_line_length: Maximum line length
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified = False
        for i in range(len(lines)):
            line = lines[i]

# Check whether it is a comment line and whether it is too long
            if line.strip().startswith('#') and len(line.rstrip()) > max_line_length:
# Find indentation
                indent = re.match(r'^(\s*)', line).group(1)

# Share the comment text
                comment_text = line.strip()[1:].strip()  # Remove # and leading spaces

# Simple strategy: Find and divide for a space for approx. 70 characters
                words = comment_text.split()
                new_comment_lines = []
                current_line = "#"

                for word in words:
                    if len(current_line + " " + word) > max_line_length - len(indent):
                        new_comment_lines.append(indent + current_line)
                        current_line = "# " + word
                    else:
                        current_line += " " + word if current_line != "#" else " " + word

                if current_line != "#":
                    new_comment_lines.append(indent + current_line)

# Replace the original line with the new commentary lines
                lines[i] = '\n'.join(new_comment_lines) + '\n'
                modified = True

        if modified:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            print(f"File {file_path} was successfully updated.")
        else:
            print(f"No long comment lines found in {file_path}.")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python split_comments.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    split_long_comment_lines(file_path)
