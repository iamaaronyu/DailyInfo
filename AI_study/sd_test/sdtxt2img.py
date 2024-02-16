

import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin

import gradio as gr

# 定义generate_image函数
def generate_image(text):
    url = "http://xwix.vip:9999"
    payload = {
        "prompt": text,  # 使用函数的参数
        "steps": 5
    }
    print(payload)

    # 发送请求到API以生成图像
    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
    r = response.json()
    print(r)

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
iface = gr.Interface(fn=generate_image, inputs="text", outputs="image")

# 启动应用，当你运行这段代码时，Gradio会提供一个URL，你可以通过浏览器访问这个界面
iface.launch()
