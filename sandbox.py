import faker
from email.mime import image

f = faker.Faker()
img = f.image(image_format="png")

print(image.MIMEImage(img).as_string())
