"""Ve icon 1024x1024 (nen tim bo goc + chu "TL") ra assets/icon-1024.png bang AppKit — khong can Pillow.
Chay: .venv/bin/python tools/make_icon.py"""
from pathlib import Path

from AppKit import (NSBezierPath, NSBitmapImageRep, NSColor, NSFont, NSFontAttributeName,
                    NSForegroundColorAttributeName, NSGradient, NSGraphicsContext, NSImage, NSMakeRect,
                    NSPNGFileType, NSString)

SIZE = 1024
OUT = Path(__file__).resolve().parent.parent / "assets" / "icon-1024.png"


def main() -> None:
    img = NSImage.alloc().initWithSize_((SIZE, SIZE))
    img.lockFocus()
    NSGraphicsContext.currentContext().setShouldAntialias_(True)
    inset = SIZE * 0.09                     # le trong suot giong icon macOS
    rect = NSMakeRect(inset, inset, SIZE - 2 * inset, SIZE - 2 * inset)
    path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, SIZE * 0.19, SIZE * 0.19)
    grad = NSGradient.alloc().initWithStartingColor_endingColor_(
        NSColor.colorWithSRGBRed_green_blue_alpha_(0.31, 0.27, 0.90, 1.0),
        NSColor.colorWithSRGBRed_green_blue_alpha_(0.49, 0.51, 1.0, 1.0),
    )
    grad.drawInBezierPath_angle_(path, -45)
    text = NSString.stringWithString_("TL")
    attrs = {
        NSFontAttributeName: NSFont.systemFontOfSize_weight_(SIZE * 0.36, 0.56),
        NSForegroundColorAttributeName: NSColor.whiteColor(),
    }
    w, h = text.sizeWithAttributes_(attrs)
    text.drawAtPoint_withAttributes_(((SIZE - w) / 2, (SIZE - h) / 2 - SIZE * 0.01), attrs)
    img.unlockFocus()

    rep = NSBitmapImageRep.alloc().initWithData_(img.TIFFRepresentation())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rep.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(str(OUT), True)
    print(OUT)


if __name__ == "__main__":
    main()
