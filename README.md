# Home Assistant Component "sonosmanual"

Home Assistant Component to define static Sonos Environment. The devices are also added if the sonos devices are not reachable. So you can switch off your devices and switch them on on demand.

## Installation

Just clone or copy this repository to your home assistant configuration directory in the subdir custom_components/sonosmanual

## Configuration

Add your Sonos entities to your configuration.yaml:

```yaml
media_player:
  - platform: sonosmanual
    hosts:
      - ip: 192.168.0.9
        name: Bathroom
      - ip: 192.168.0.10
        name: TV
```

The ip is the static ip of your Sonos device. The name is the entit yname it should get. 