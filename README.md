# Discogs Wantlist Notifier

Home Assistant Custom Integration for your Discogs Wantlist.

Monitors your Discogs wantlist for items matching your price and condition preferences, and sends notifications to your mobile devices.

## Features

- Fetches your Discogs wantlist and checks marketplace listings for good offers
- Filters by configurable media and sleeve condition thresholds
- Reads max prices from your wantlist item notes (format: `max price: €XX.XX`)
- Sends rich notifications via Home Assistant's notify service
- Secure token storage via Home Assistant's encrypted config entry

## Installation

### Via HACS

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots in the top-right corner and select "Custom repositories"
4. Add `https://github.com/j-danner/discogs_wantlist_notifier` as an Integration repository
5. Click Install

### Manual Installation

Copy the `custom_components/discogs_wantlist_notifier/` directory into your Home Assistant's `custom_components/` directory.

## Configuration

1. Generate a Discogs Personal Access Token at https://www.discogs.com/settings/developers
2. In Home Assistant, go to Configuration → Integrations
3. Click "Add Integration" and search for "Discogs Wantlist Notifier"
4. Enter your Discogs token
5. Configure your preferred conditions and select a notification target

## Service

This integration provides the `discogs_wantlist_notifier.check_offers_in_wantlist` service. All configuration is handled through the UI, so no service data parameters are required.

## Requirements

- Home Assistant 2022.12 or newer
- HACS 1.33.0 or newer (if installed via HACS)
- A Discogs Personal Access Token

## Support

For issues and feature requests, please use the [issue tracker](https://github.com/j-danner/discogs_wantlist_notifier/issues).
