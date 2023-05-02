# Mote Broker

Mote is an expansion/modification of the MQTT protocol.  You can read more about MQTT at https://mqtt.org/.  The mote broker is a lot like an API server, but without any custom code needed, no plugins, no boilerplate, it works right out of the box..  There's a database, but if you want models, they would only need to be defined on the client side..

# The basics of MQTT and Mote - an example
In Mote and MQTT you can publish messages like so:
```
topic=light/bedroom/set_on, data=1, retain=False
```
This might be used to turn on a bedroom light.

After the light turns on, it may respond with a publish that looks like:
```
topic=light/bedroom/is_on, data=1, retain=True
```
and this message will be retained in the database for any interested clients.

A webapp might subscribe to the topic `light/+/is_on` to get a list of lights that are on. The response from the server is where Mote starts to differ from MQTT....

A typical MQTT server would respond with multiple separate publish messages/packets, and one might be `topic=light/bedroom/is_on, data=1, qos=1` to indicate the state of the bedroom light, and you might have another for `light/livingroom/is_on`, etc....

The mote-broker will always respond to subscriptions with the exact same topic as the subscription, this makes it a bit easier to know where a message is supposed to go, and it allows us to package multiple messages together in a JSON tree. Mote also allows clients to specify with a flag called `sync` if they want  an immediete response from the broker containing all the relevant retained messages.

If a mote client subscribes to `topic=light/+/is_on, sync=True`, it's going to get an immediate JSON response like so:
```
topic=light/+/is_on,
data={
   bedroom: 1,
   livingroom: 0,
},
```
This tells us all the information about which lights are `on` in one message.  If any of the `is_on` topics change, the mote-broker will send the client an update like so:
```
topic=light/+/is_on,
data={
   livingroom: 1,
},
```

Clients can, similarly, publish blocks of messages, so, say when a light first connects, it might want to publish all of its properties like so:
```
topic=light/bedroom/+,
tree=True,
data={
  is_on: 1,
  brightness: 55,
  color: "#FFFFFF",
}
```
note the `tree` flag to indicate that the payload contains a tree that should get spead into many messages (sometimes called rows)

# Performance
The mote-broker uses trees and recursion to allow wide spanning subscriptions with many inflight messages being distributed to many different devices of varying types.  It is designed to scale as linearly as possible in terms of number of wildcards in both subscriptions and publish messages.  A separate process is responsible for retaining messages in a database, and as such retaining happens as quickly as possible while also not impacting performance whatsoever.

# Installation/Setup
Mote broker has been designed to have as few dependencies as possible
It has been tested with `python3.8` and above, it should have no issue running on anything that can run python.  For now, you'll need to install `python3-venv` to get working, and you may need other packages to get that working (I'll add them here if I become aware of them.

Once you have `python3-venv`, you can take the following steps to get setup:
```
cd mote-broker
python3 -m venv venv
source activate
pip install -r requirements.txt
```

# Running
```
 source activate
 python app.py
```

# You're still here
If you've read this far it's because you somehow understand our cumbersome explaination of this extremely abstract project and you want to know more... you aren't going to be impressed until you see what this puppy can really do... 

this section is being added today May 2 2023, I'm making lunch rn I'm just saving my spot


## The Message Loop
At the heart of an MQTT broker is the message loop.  Instead of processing one message at a time, with Mote, the broker's message loop processes lists of messages (or rows). When the Mote broker recieves a publish with the `tree` flag, it can recurse through that tree and turn it into a list of rows and put the entire list on the message loop.  Whenever a new list of rows is added to the message loop, it can recurse through a topic tree of current subscriptions and can build a single message for each subscription to send back to each interested client.  In this regard, Mote broker is a tree multiplexer, it can take one tree as input, and transform the input into many output formats.
