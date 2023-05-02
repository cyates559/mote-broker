# mote-broker

Mote is an expansion/modification of the MQTT protocol.  You can read more about MQTT at https://mqtt.org/.

# The basics of MQTT and Mote - An example
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

A webapp might subscribe to the topic `light/+/is_on` to get a list of lights that are on. The response from the server is where Mote starts to differ from MQTT.  A typical MQTT server would respond with multiple separate publish messages/packets, and one might be `topic=light/bedroom/is_on, data=1, qos=1` to indicate the state of the bedroom light, and you might have another for `light/livingroom/is_on`, etc....

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
The mote-broker uses trees and recursion to allow wide spanning subscriptions with many inflight messages being distributed to many different devices of varying types.  
