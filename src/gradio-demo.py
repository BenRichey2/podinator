#import random
#
#import numpy as np
#import gradio as gr
#
#def sepia(input_img):
#    sepia_filter = np.array([
#        [0.393, 0.769, 0.189],
#        [0.349, 0.686, 0.168],
#        [0.272, 0.534, 0.131]
#    ])
#    sepia_img = input_img.dot(sepia_filter)
#    sepia_img /= sepia_img.max()
#    return sepia_img
#
#def greet(name, is_morning, temperature):
#    salutation = "Good morning" if is_morning else "Good evening"
#    greeting = f"{salutation}, {name}. It is {temperature} degrees today."
#    celsius = (temperature - 32) * 5 / 9
#    return greeting, round(celsius, 2)
#
#def random_response(message, history):
#    return random.choice(["Yes", "No"])
#
##demo = gr.Interface(
##    fn=greet,
##    inputs=["text", "checkbox", gr.Slider(0, 100)],
##    outputs=["text", "number"],
##)
##demo = gr.Interface(
##    sepia,
##    gr.Image(),
##    "image"
##)
#demo = gr.ChatInterface(
#    random_response,
#    theme=gr.themes.Soft()
#)
#
#if __name__ == "__main__":
#    demo.launch(show_api=False)
#
#
#import gradio as gr
#import numpy as np
#import time
#
## define core fn, which returns a generator {steps} times before returning the image
#def fake_diffusion(steps):
#    for _ in range(int(steps)):
#        time.sleep(1)
#        image = np.random.random((600, 600, 3))
#        yield image
#    image = np.ones((1000,1000,3), np.uint8)
#    image[:] = [255, 124, 0]
#    yield image
#
#
#demo = gr.Interface(
#    fake_diffusion,
#    inputs=gr.Slider(1, 10, 3, step=1.0),
#    outputs="image"
#)
#
## define queue - required for generators
#demo.queue()
#
#demo.launch()

import gradio as gr

def greet(name):
    return "Hello " + name + "!"

with gr.Blocks() as demo:
    name = gr.Textbox(label="Name")
    output = gr.Textbox(label="Output box")
    greet_btn = gr.Button("Greet")
    greet_btn.click(
        fn=greet,
        inputs=name,
        outputs=output,
        api_name="greet"
    )