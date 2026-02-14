# Task #1

Add a dropdown / selector to the config flow as the first field. Two options `The Masjid App` and `Madina Apps`. Provider selector is not needed for reconfigure flow.

If `The Masjid App` use the current workflow.

If `Madina Apps` then use new workflow for madinaapps.com.

Change `CONF_MASJID_ID` everywhere to make sure it accepts and work with strings instead of just numbers.

In `_async_validate_masjid_id`, check which option is selected. If `Madina Apps`, then use the URL like `https://services.madinaapps.com/kiosk-rest/clients/masjidquba/settingsbyalias`,
where `masjidquba` is the entered ID.

Sample Response

```json
{
  "clientId": 235,
  "clientName": "Masjid Quba WA",
  "clientLogo": "https://media.madinaapps.com/prod/kiosk-cp-media/client_235/logo/TWFzamlkIFF1YmEgV0ExNjU0NjIyNjA1OTgz.jpeg",
  "clientAlias": "MasjidQuba",
  "currency": "USD",
  "paymentSuccessMessage": "Thank you for your payment. Transaction Completed Successfully.",
  "socialFacebookUrl": "https://www.facebook.com/MasjidQubaWA/",
  "socialTwitterUrl": "",
  "socialGooglePlusUrl": "",
  "socialWhatsapp": "https://chat.whatsapp.com/GV2keXtiKueB9cxNTsRZCY",
  "paymentGatewayId": 309,
  "profileName": "Centro Islamico PR",
  "gateway": "Stripe",
  "paymentGatewayPublicKey": "pk_live_51KpEWkAtNS28HVeTnfZ5G0bEAM0Y2XcSEp598BPNwpIcG5BRUICdRLOHiEN9C2BLrxr093y92brYzp72gSeU1Fmf007PITF28v",
  "timeZone": "US/Pacific",
  "website": "https://aacwashington.org/masjid-quba/",
  "appSettings": [
    { "key": "APP_ANDROID_DOWNLOAD_URL", "value": "0", "type": "text" },
    { "key": "APP_IOS_DOWNLOAD_URL", "value": "0", "type": "text" },
    { "key": "APP_SHOW_FRIDAY_IQAMAH", "value": "false", "type": "boolaen" },
    { "key": "APP_VERSION_ANDROID", "value": "0", "type": "text" },
    { "key": "APP_VERSION_IOS", "value": "0", "type": "text" },
    { "key": "CLIENT_HAS_MOBILE_APP", "value": "false", "type": "" },
    { "key": "CLIENT_HAS_MOBILE_KIOSK", "value": "false", "type": "" },
    { "key": "DP_SUCCESS_ADDITIONAL_MESSAGE", "value": " ", "type": "" },
    { "key": "FCM_KEY_CODE", "value": "KEY_1", "type": "text" },
    { "key": "KIOSK_PAYMENT_READER", "value": "MSR", "type": "text" },
    {
      "key": "KIOSK_SHOW_EMPLOYEE_SIGNIN",
      "value": "false",
      "type": "boolaen"
    },
    { "key": "MA2_TOKEN", "value": "0", "type": "text" },
    { "key": "MEMBERSHIP_PAYMENT_OPTION_ID", "value": "0", "type": "text" },
    { "key": "MP_ACCEPT_DONATIONS", "value": "false", "type": "boolaen" },
    { "key": "MP_ADDRESS_MANDATORY", "value": "false", "type": "boolaen" },
    { "key": "MP_CHECK_IN", "value": "false", "type": "" },
    { "key": "MP_DAILY_BOOKING_OPEN_TIME", "value": "0", "type": "" },
    { "key": "MP_DAILY_PRAYER_BOOKING", "value": "false", "type": "" },
    { "key": "MP_DOB_TYPE", "value": "YEAR", "type": "text" },
    { "key": "MP_EID_BOOKING_OPEN_DAYS_BEFORE", "value": "3", "type": "text" },
    { "key": "MP_EID_BOOKING_OPEN_TIME", "value": "10:00 AM", "type": "text" },
    { "key": "MP_EID_DATE", "value": "2021-05-13", "type": "text" },
    { "key": "MP_EID_PRAYER_BOOKING", "value": "false", "type": "text" },
    {
      "key": "MP_EMERGENCYCONTACT_MANDATORY",
      "value": "false",
      "type": "boolaen"
    },
    { "key": "MP_FAMILY_MEMBER_DOB", "value": "true", "type": "text" },
    { "key": "MP_FRIDAY_BOOKING_OPEN_DAYS_BEFORE", "value": "8", "type": "" },
    { "key": "MP_FRIDAY_BOOKING_OPEN_TIME", "value": "10:00 AM", "type": "" },
    { "key": "MP_FRIDAY_PRAYER_BOOKING", "value": "false", "type": "" },
    { "key": "MP_JUMMA_QR_INFO", "value": "false", "type": "" },
    { "key": "MP_LOGIN_TO_HOME", "value": "true", "type": "" },
    { "key": "MP_MY_PRAYER_BOOKINGS", "value": "false", "type": "" },
    { "key": "MP_PRAYER_BOOKING_TERMS", "value": " ", "type": "" },
    { "key": "MP_PROFILE", "value": "false", "type": "text" },
    { "key": "MP_PROGRAM_SERVICES", "value": "false", "type": "" },
    { "key": "MP_QR_INFO", "value": "false", "type": "" },
    {
      "key": "MP_QR_INFO_TEXT",
      "value": "<ol><li>This is your permanent QR code</li><li>Scan the QR code every time you enter the masjid</li><li>Jumu'ah salah will be a first-come, first-serve basis for musallees with QR code</li></ol>",
      "type": ""
    },
    {
      "key": "MP_SEPERATE_EMAIL_PHONE_FIELD_REGISTRATION",
      "value": "true",
      "type": ""
    },
    { "key": "MP_SHOW_ADDRESS_ON_SIGNUP", "value": "false", "type": "" },
    { "key": "MP_SHOW_DOB_ON_REGISTRATION", "value": "true", "type": "" },
    { "key": "MP_SHOW_PRAYER_REGISTRATION", "value": "false", "type": "" },
    { "key": "MP_SHOW_VACINATION", "value": "false", "type": "" },
    {
      "key": "MP_SIGNIN_INFO_TEXT",
      "value": "<ol><li>Signup for a one time registration.</li><li>A permanent QR CODE will be assigned to you that can be used for every salah</li></ol>",
      "type": ""
    },
    { "key": "MP_TRANSACTION", "value": "true", "type": "" },
    { "key": "REDIRECT_PAYMENT_TO_V2", "value": "true", "type": "boolaen" },
    {
      "key": "SMS_OTHER_COMMAND_MESSAGE",
      "value": "[%s] - Invalid message! Either send DONATE 10 to donate %s 10 OR SUBSCRIBE to register for %s Text-to-Donate Service!",
      "type": "text"
    },
    { "key": "TERMINAL_LOCATION_ID", "value": "0", "type": "text" },
    { "key": "TERMINAL_PAYMENT_OPTION_ID", "value": "0", "type": "text" }
  ]
}
```

Pick `clientName` as the masjid name.
Save `clientId` as a new value media apps client ID (similar to how `self.async_create_entry` is doing). This is needed later for fetching the prayer times.
Save selected provider as a new value prayer time provider (similar to how `self.async_create_entry` is doing). Internally save values as `themasjidapp` or `madinaapp`.

Update `async_set_unique_id` duplicate detection logic to use prefix of `themasjidapp` or `madinaapp` (reuse constants) before the masjid ID.

Update docs and params correctly for all modified code.

Place translations in correct location.

Update README to indicate that this this add on supports both websites. Blend in the changes to make docs seamless.

Use context7.

---
