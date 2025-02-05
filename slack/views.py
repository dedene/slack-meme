from flask import Flask, request
from slack.models import Memegen, Slack, parse_text_into_params, image_exists

app = Flask(__name__)

memegen = Memegen()
slack = Slack()

@app.route("/", methods=["GET", "POST"])
def meme():
    data = request.form if request.method == "POST" else request.args
    token, text, channel_id, channel_name, response_url, user_id = [data[key] for key in ("token", "text", "channel_id", "channel_name", "response_url", "user_id")]
    app.logger.debug("Got message from channel: \"%s\"", channel_id)
    app.logger.debug("Got respond_url: \"%s\"", response_url)
    text = text.strip()

    if token != slack.SLASH_COMMAND_TOKEN:
        return "Unauthorized."

    if text.lower() in ("help", ""):
        return memegen.help()

    if text.lower() == "templates":
        return memegen.template_list

    app.logger.debug("text: \"%s\"", text)

    template, top, bottom = parse_text_into_params(text)
    app.logger.debug("parsed text: template=\"%s\" top=\"%s\" bottom=\"%s\"", template, top, bottom)

    if template in memegen.valid_templates:
        meme_url = memegen.build_url(template, top, bottom)
    elif image_exists(template):
        meme_url = memegen.build_url("custom", top, bottom, template)
    else:
        app.logger.debug("bad template: \"%s\"", template)
        app.logger.debug("valid templates: \"%s\"", memegen.valid_templates)
        return memegen.bad_template(template)

    payload = {"channel": channel_id, "as_user": False, "replace_original": False, "response_type": "in_channel"}
    user = slack.find_user_info(user_id)
    payload.update(user)

    if bottom:
      attachments = [{"image_url": meme_url, "fallback": "; ".join([top, bottom])}]
    else:
      attachments = [{"image_url": meme_url, "fallback": "; ".join([top])}]
    payload.update({"attachments": attachments})
    
    app.logger.debug("payload: \"%s\"", payload)
    try:
        if channel_name == "directmessage":
          slack.post_meme_to_webhook(response_url, payload)
        else:
          slack.post_meme_to_webhook(None, payload)
    except Exception as e:
        app.logger.error("Error: \"%s\"", e)
        return e

    return "", 200
