# Zoho to MXRoute Split Delivery

I have user two mail server. Zoho because they are super cheap and I don't have to worry about any sort of email configuration (just set the DNS and forget), and more recently I purchased a [MXRoute Lifetime Plan](https://docs.mxroute.com/docs/presales/lifetime.html). I wanted to use MXRoute for all my random projects and services I deploy so I don't have to pay for another email seat on Zoho, however I ran into one issue. MXRoute does not support *split delivery*. 

### The Delivery Problems

**1. Relay not permitted:** MXRoute refuses to accept the email from Zoho because it didn't recognize itself as authorized to handle mail for that domain. The server needed to be explicitly told it could accept mail for this domain. Since MXRoute does not support split delivery, we cannot do this.

```
user@example.com, ERROR CODE :550 - Relay not permitted
```

**2. Local Delivery Loop:** When sending FROM MXRoute to Zoho, MXRoute assumed it should deliver locally (since it "manages" the domain) rather than checking MX records. The email then bounces since that user does not exist on MXRoute's servers.

The "Use this server to handle my e-mails" checkbox creates a catch 22:

- **Checkbox Checked:** Fixes incoming mail but breaks outgoing mail (Zoho to Mxroute works, but MXRoute to Zoho fails)
- **Checkbox Unchecked:** Fixes outgoing mail but breaks incoming mail (Zoho to Mxroute fails, but MXRoute to Zoho works)

This toggle essentially controls whether MXRoute thinks it "owns" the domain, but split delivery requires it to act like it owns the domain for incoming mail AND act like it doesn't own the domain for outgoing mail - a logical contradiction that standard email servers cannot resolve.

### Resolution

After a whole lot of troubleshooting and searching for an answer I came across [this blog post](https://blog.alexwang.net/google-workspace-mxroute-split-delivery/) from *Alex Wang*. We set up a new MX record (ex: `zoho.example.com`) that points to our Zoho mail server. Then in MXRoute we create a forwarder that points to that MX record:

```
user@example.com --> user@zoho.example.com
```

The issue is that we would have to add a forwarder for every user in Zoho, and as the words of a wise scolar once said, "Ain't nobady got time for that" - the internet. This script pulls data from both the Zoho and MXRoute APIs and automaticly creates that fowarder for you. 

> **TLDR:** It automaticly pulls your emails from Zoho and creates forwarders in MXRoute. 


## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

### Zoho

> [!NOTE]
> At this time Zoho does not support retrival of *shared inboxes* via their API. Those should be the only address that will have to be manually added to MXRoute.

In Zoho you are going to have to go to the [Zoho Developer Console](https://accounts.zoho.com/developerconsole) and create a *Self Client*. Once that has been generated please set the following environmt variables:

* `CLIENT_ID` - Under the Client Secret tab of your *Self Client*
* `CLIENT_SECRET` - Under the Client Secret tab of your *Self Client*
* `ORGANIZATION_ID` - Found in your [Mail Admin](https://mailadmin.zoho.com/cpanel/home.do#organization/profile) console

For more information please see [Zoho's OAuth 2.0 Guide](https://www.zoho.com/mail/help/api/using-oauth-2.html). 

### MXRoute

> [!NOTE]
> DirectAdmin newer api does not yet support email forwarders. Due to this, the scripts uses the [legacy API](https://docs.directadmin.com/developer/api/legacy-api.html).

Log into DirectAdmin and head to `Advanced Features > Login Keys`. Create a new key and give it the following permissions:

- `CMD_API_SHOW_DOMAINS`
- `CMD_API_EMAIL_FORWARDERS`
- `CMD_EMAIL_FORWARDER`
- `CMD_EMAIL_FORWARDER_MODIFY`

Make sure to uncheck *Has expiry date* is you don't want the key to expire. Then just set the following environment variables:

- `USER_ID` - Username of the admin user without `@domain.tld` at the end
- `PASSWORD` - Login key you generated
- `SERVER` - Host of you MXRoute server (ex: `https://subdomain.mxrouting.net:2222`)

### Optional 

- `CRON_SCHEDULE` - By default set to `*/5 * * * *` (every 5 minutes). Only change if you want the cron to run on a different interval. 


## Deploy

To deploy this project, first copy the `.env-example` and set the envrionment variables in there:

```bash
cp .env-example .env
```

Once you have done that, you can run the docker container and pass in your `.env` file:

```bash

```


## Run Locally

Clone the project

```bash
git clone https://link-to-project
cd project-repo
```

Configure the `.env` as seen in the [*deploy*](#deploy) section

### Docker


### Python
