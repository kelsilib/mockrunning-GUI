from PIL import Image, ImageDraw
from pathlib import Path

scale = 4
image = Image.new("RGBA", (256 * scale, 256 * scale), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8*scale,8*scale,248*scale,248*scale),radius=52*scale,fill="#f1ead9")
points=[(65,192),(65,83)]
def curve(start,control,end):
    for step in range(1,25):
        t=step/24
        points.append(((1-t)**2*start[0]+2*(1-t)*t*control[0]+t*t*end[0],(1-t)**2*start[1]+2*(1-t)*t*control[1]+t*t*end[1]))
curve((65,83),(65,61),(87,61))
points.append((174,61))
curve((174,61),(202,61),(202,88))
curve((202,88),(202,116),(174,116))
points.append((117,116))
curve((117,116),(89,116),(89,144))
curve((89,144),(89,172),(117,172))
points.append((189,172))
draw.line([(x*scale,y*scale) for x,y in points],fill="#a76243",width=15*scale,joint="curve")
for x,y in [(65,192),(189,172)]:
    r=13*scale
    draw.ellipse((x*scale-r,y*scale-r,x*scale+r,y*scale+r),fill="#a76243")
    r=4*scale
    draw.ellipse((x*scale-r,y*scale-r,x*scale+r,y*scale+r),fill="#fff7e9")
image = image.resize((256,256),Image.Resampling.LANCZOS)
image.save(Path(__file__).parent / "assets/route-studio.ico",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
