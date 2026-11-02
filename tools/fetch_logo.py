# usage: python -I tools/fetch_logo.py  -> film/assets/logo.svg, logo_white.svg, logo_allwhite.svg
# Akaike's marks belong to Akaike, so they are fetched from its website instead of being committed. The two extra versions recolour the same file for dark panels.
import urllib.request
URL = 'https://cdn.prod.website-files.com/65780598bc98530c125f5b9e/6932805be03f95d34a031309_Primary%20Logo%20-%20Blue%26Black.svg'
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
svg = urllib.request.urlopen(req).read().decode()
open('film/assets/logo.svg', 'w').write(svg)
open('film/assets/logo_white.svg', 'w').write(svg.replace('#0B0D0B', '#FFFFFF'))
open('film/assets/logo_allwhite.svg', 'w').write(svg.replace('#2699FB', '#FFFFFF').replace('#0B0D0B', '#FFFFFF'))
