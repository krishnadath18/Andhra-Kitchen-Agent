from ui.styles import get_global_styles

s = get_global_styles()
print(f"Length: {len(s)}")
print(f"First 300 chars:\n{s[:300]}")
print(f"\nHas <style> tag: {'<style>' in s}")
print(f"Has </style> tag: {'</style>' in s}")
print(f"Has <link> tag: {'<link' in s}")
print(f"\nLast 100 chars:\n{s[-100:]}")
