import subprocess
import sys
import os
import shutil
import gradio as gr
import modelscope_studio as mgr
import uvicorn
from fastapi import FastAPI
import warnings
warnings.filterwarnings("ignore")

from src.pipeline import chat_pipeline

# os.environ["DASHSCOPE_API_KEY"] = "INPUT YOUR API KEY HERE"
os.environ["is_half"] = "True"

# 安装musetalk依赖
os.system('mim install mmengine')
os.system('mim install "mmcv==2.1.0"')
os.system('mim install "mmdet==3.2.0"')
os.system('mim install "mmpose==1.2.0"')
# os.system('pip install gradio') # 安装Gradio 5.0,目前创空间暂不支持，本地可选择5.0版本
shutil.rmtree('./workspaces/results', ignore_errors= True)


def create_gradio():
    with gr.Blocks() as demo:   
        gr.Markdown(
            """
            <div style="text-align: center; font-size: 32px; font-weight: bold; margin-bottom: 20px;">
            Chat with Digital Human
            </div>  
            """
        )
        with gr.Row():
            with gr.Column(scale = 2):
                user_chatbot = mgr.Chatbot(
                    label = "Chat History 💬",
                    value = [[None, {"text":"您好，请问有什么可以帮到您？您可以在下方的输入框点击麦克风录制音频或直接输入文本与我聊天。"}],],
                    avatar_images=[
                        {"avatar": os.path.abspath("data/icon/user.png")},
                        {"avatar": os.path.abspath("data/icon/qwen.png")},
                    ],
                    height= 500,
                    ) 

                with gr.Row():
                    avatar_name = gr.Dropdown(label = "数字人形象", choices = ["Avatar1 (通义万相)", "Avatar2 (通义万相)", "Avatar3 (MuseV)"], value = "Avatar1 (通义万相)")
                    chat_mode = gr.Dropdown(label = "对话模式", choices = ["单轮对话 (一次性回答问题)", "互动对话 (分多次回答问题)"], value = "单轮对话 (一次性回答问题)")
                    tts_module = gr.Dropdown(label = "TTS选型", choices = ["GPT-SoVits", "CosyVoice"], value = "CosyVoice")
                    avatar_voice = gr.Dropdown(label = "TTS音色", choices = ["longxiaochun (CosyVoice)", "longwan (CosyVoice)", "longcheng (CosyVoice)", "longhua (CosyVoice)", "少女 (GPT-SoVits)", "女性 (GPT-SoVits)", "青年 (GPT-SoVits)", "男性 (GPT-SoVits)"], value="longwan (CosyVoice)")
                    chunk_size = gr.Slider(label = "每次处理的句子最短长度", minimum = 0, maximum = 30, value = 5, step = 1) 

                user_input = mgr.MultimodalInput(sources=["microphone"])

            with gr.Column(scale = 1):
                video_stream = gr.Video(label="Video Stream 🎬 (基于Gradio 5测试版，网速不佳可能卡顿)", streaming=True, height = 600, scale = 1)  
                stop_button = gr.Button(value="停止生成")

        # Use State to store user chat history
        user_messages = gr.State([{'role': 'system', 'content': None}])
        user_processing_flag = gr.State(False)
        lifecycle = mgr.Lifecycle()

        # loading TTS Voice
        avatar_voice.change(chat_pipeline.load_voice, 
            inputs=[avatar_voice, tts_module], 
            outputs=[user_input]
            )
        lifecycle.mount(chat_pipeline.load_voice,
            inputs=[avatar_voice, tts_module],
            outputs=[user_input]
        )

        # Submit
        user_input.submit(chat_pipeline.run_pipeline,
            inputs=[user_input, user_messages, chunk_size, avatar_name, tts_module, chat_mode], 
            outputs=[user_messages]
            )
        user_input.submit(chat_pipeline.yield_results, 
            inputs=[user_input, user_chatbot, user_processing_flag],
            outputs = [user_input, user_chatbot, video_stream, user_processing_flag]
            )

        # refresh
        lifecycle.unmount(chat_pipeline.stop_pipeline, 
            inputs = user_processing_flag, 
            outputs = user_processing_flag
            )

        # stop
        stop_button.click(chat_pipeline.stop_pipeline, 
            inputs = user_processing_flag, 
            outputs = user_processing_flag
            )
        
    return demo.queue()

if __name__ == "__main__":
    app = FastAPI()
    gradio_app = create_gradio()
    app = gr.mount_gradio_app(app, gradio_app, path='/')
    uvicorn.run(app, port = 7860)