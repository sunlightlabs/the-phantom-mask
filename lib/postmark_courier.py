from postmark_inbound import PostmarkInbound

def parse_postmark_json(json_data):
    inbound = PostmarkInbound(json=json_data)


