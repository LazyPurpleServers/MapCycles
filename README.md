# LPS-Maplists
LazyPurple’s TF2 Servers Maplist

This repository lists all of the maps that are currently running on the LP servers. This list has been made public so that the general public can familiarize themselves with the maps that are available on our servers. Once maps are run on LPS, they go on a long cooldown, so most folks don't get to see the full extent of our map list.

Please report any map errors in our public Discord channel! With such a large maplist and several servers to maintain, there's always a possibility that a map won't download correctly or may cause a client and/or server crash. Your error reporting is a big help to us and we greatly appreciate it. Additionally, we have an entire channel dedicated to discussion of maps. Stop on by and bring a map suggestion with you!

Main Website: https://lazypurple.com/ 

Discord invite: https://discord.gg/XG9Vm4rJuA

Server Fastdl: https://lazypurple.com/tf/fastdl/




(The details below are for those with writing permissions, reserved for Community Managers and Staff. You can read this if you don't have those roles if you want insight to how we do things, but you will not be able to apply this knowledge.)


How to add a Workshop Map to a rotation;

To add a map from the Steam Workshop to a rotation, first find the page for the map you want in question. You will need to do two things; both Subscribe to the map and get the Workshop ID for the map. When you Subscribe to the map, make sure your Steam Client is open, and you will be able to find the newly downloaded map in your directory; Steam\steamapps\workshop\content\440. The number 440 is the game ID for Team Fortress 2. If you sort this folder by date modified, the most recent folder should contain the map you just Subscribed to.

Open the folder for the map you wish to add to the servers, and write down the file name for the map. This will be necessary to put it on rotation. As well, the name of the folder for the map you just Subscribed to is the Workshop ID. This is the first method of finding it. The second method is by looking at the link to the map itself. In the link, there should be a ten digit code that will also be the Workshop ID. Remember that the workshop ID will never contain any letters or special characters, ONLY numbers.

After this, head to the rotation that you wish to add to. Remember that this method does NOT work for the MvM Servers. You will format it like so; "tf2ware_ultimate" { "workshopid" "3413262999" }. The name "tf2ware_ultimate" is the filename for the map, and the numbers "3413262999" is the Workshop ID. If the map updates, you will need to update the name/version string of the map, but the Workshop ID will stay the same. If the map is ever added to TF2, all you need to do is remove the second part of the equation and keep the version string, like so; "tf2ware_ultimate" { }.

Remember to try to keep the maps in rotation categories in alphabetical order where possible, and try to imitate the formatting of the rest of the rotation. If you need help, contact Gravidea or DosMike for more information!


How to add a FastDL Map to a rotation;

Coming Soon...
