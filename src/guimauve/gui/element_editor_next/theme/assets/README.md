# Theme assets

## Fonts

Manrope, OFL 1.1 (`fonts/OFL.txt`). Static instances generated from the variable font of Google Fonts:

```
curl.exe -L -o Manrope-variable.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf"
uvx --from fonttools fonttools varLib.instancer Manrope-variable.ttf wght=400 --static --update-name-table -o fonts/Manrope-Regular.ttf
uvx --from fonttools fonttools varLib.instancer Manrope-variable.ttf wght=500 --static --update-name-table -o fonts/Manrope-Medium.ttf
uvx --from fonttools fonttools varLib.instancer Manrope-variable.ttf wght=600 --static --update-name-table -o fonts/Manrope-SemiBold.ttf
uvx --from fonttools fonttools varLib.instancer Manrope-variable.ttf wght=700 --static --update-name-table -o fonts/Manrope-Bold.ttf
```

## Icons

Lucide, ISC (`icons/LICENSE`), from `lucide-static` 1.49.0, copied unchanged from its `icons/` folder:

```
curl.exe -L -o lucide.tgz https://registry.npmjs.org/lucide-static/-/lucide-static-1.49.0.tgz
tar -xzf lucide.tgz
```

Each SVG needs a member in `Icon` (`theme/icons.py`).

## Logo

`logo/guimauve.svg`: direction D1 (overlap), bright tones, from the mockups of the editor redesign. The overlap is
a path rather than a clip path, which Qt SVG ignores.
