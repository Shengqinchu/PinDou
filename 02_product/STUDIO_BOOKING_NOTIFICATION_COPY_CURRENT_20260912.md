# 现行顾客预约通知模板

核对时间：2026-09-12T20:31:16.514367+00:00。以下直接来自线上发布文件，没有改写生产文案。

邮件标题格式：`小狗拼豆铺 · {通知标题}` / `PinDou Puppy · {notification title}`。短信正文使用通知标题加换行加正文。微信使用字段式卡片，见状态报告。

占位符：`{name}`称呼，`{date}`日期，`{start}`开始时间，`{end}`结束时间，`{guests}`人数，`{address}`店铺地址，`{url}`该顾客自己的预约详情链接。

当前地址：8 Hughson St N, Hamilton, ON L8R 0B1

## 提交申请后

中文标题：预约申请已收到

```text
{name}，你的预约申请已收到，正在等待店主确认。
{date} {start}–{end} · {guests} 人
汉密尔顿当地时间
查看预约或联系店主：{url}
```

英文标题：Booking request received

```text
Hi {name}, your booking request is waiting for the host to confirm.
{date} {start}–{end} · {guests} guest(s)
Hamilton local time
View your booking or message the host: {url}
```

## 店主确认后

中文标题：预约成功

```text
{name}，店主已确认你的预约。
{date} {start}–{end} · {guests} 人
汉密尔顿当地时间
地址：{address}
查看预约或联系店主：{url}
```

英文标题：Booking confirmed

```text
Hi {name}, the host has confirmed your booking.
{date} {start}–{end} · {guests} guest(s)
Hamilton local time
Address: {address}
View your booking or message the host: {url}
```

## 取消后

中文标题：预约已取消

```text
{name}，你在 {date} {start}–{end} 的预约已取消。
如需重新预约或联系店主：{url}
```

英文标题：Booking cancelled

```text
Hi {name}, your booking for {date} {start}–{end} has been cancelled.
View details or contact the host: {url}
```

## 到店前两小时

中文标题：到店提醒

```text
{name}，你在小狗拼豆铺的预约即将开始。
{date} {start}–{end} · {guests} 人
汉密尔顿当地时间
地址：{address}
查看预约或联系店主：{url}
```

英文标题：Your visit is coming up

```text
Hi {name}, your visit to PinDou Puppy is coming up.
{date} {start}–{end} · {guests} guest(s)
Hamilton local time
Address: {address}
View your booking or contact the host: {url}
```

## 邮件呈现与当前边界

邮件为最多560px宽的简洁HTML，标题、正文、查看预约、修改提醒设置；也提供纯文本正文。没有PDF附件或ICS日历附件。
预约成功邮件当前没有独立的项目名称、预约编号、价格或停车说明区块；链接指向详细预约页面。没有在本次状态整理中修改这些文案。
公开来源为已部署服务的customer-notification-copy.json和customer_notifications.py；对应仓库文案在05_studio/src/content/customer-notifications.json。
