import requests
import io
import base64
from PIL import Image, PngImagePlugin

import gradio as gr
import numpy as np

# 定义generate_image函数
def generate_image(text, input_image):
    # url = "http://xwix.vip:9999"

    # 假设 input_image 是一个 numpy.ndarray 对象
    # 你需要将其转换为 PIL.Image 对象才能使用 save 方法
    input_image_pil = Image.fromarray(np.uint8(input_image))

    # 现在 input_image_pil 是一个 PIL.Image 对象，你可以调用 save 方法了
    buffered = io.BytesIO()
    input_image_pil.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # 构造payload，包括Base64编码的图像
    payload = {
        "prompt": text,  # 使用函数的参数
        "steps": 10,
        "init_images": [img_base64],  # 将图像数据作为列表元素
        "seed": 1578029778,

    }
    # print(payload)

    # 发送请求到API以生成图像
    response = requests.post(url=f'{url}/sdapi/v1/img2img', json=payload)
    r = response.json()
    # print(r)

    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

        png_payload = {
            "image": "data:image/png;base64," + i
        }
        response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response2.json().get("info"))
        image.save('output.png', pnginfo=pnginfo)
        # 打开图片并展示出来
        # image.show()
        return image

# 创建Gradio界面
iface = gr.Interface(fn=generate_image, inputs=["text", "image"], outputs="image")

# 启动应用，当你运行这段代码时，Gradio会提供一个URL，你可以通过浏览器访问这个界面
iface.launch()
