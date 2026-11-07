#!/bin/sh
# PinDou inbound-only host firewall. Installed as /usr/local/sbin/pindou-firewall and run by
# pindou-firewall.service. See 07_ops/SERVER_HARDENING_BACKUP_20261107.md.
#
# Allows SSH (22), ICMP, DHCP and replies to the server's own connections (Cloudflare tunnel,
# DNS, NTP, WeChat/SMS APIs); drops every other inbound packet, so a service that listens on
# 0.0.0.0 by mistake (like rpcbind did) is never reachable. The site itself only arrives
# through the outbound Cloudflare tunnel.
#
# Deliberately not ufw: ufw also hooks OUTPUT and accepts loopback traffic before
# cnproxy-guard's OUTPUT rules, which would let the owner's VPN account reach local services.
# This script never touches OUTPUT. fail2ban inserts its own chain at the top of INPUT.
set -e

if [ "$1" = stop ]; then
  for tool in iptables ip6tables; do
    $tool -D INPUT -j PINDOU_IN 2>/dev/null || true
    $tool -F PINDOU_IN 2>/dev/null || true
    $tool -X PINDOU_IN 2>/dev/null || true
  done
  exit 0
fi

iptables -N PINDOU_IN 2>/dev/null || iptables -F PINDOU_IN
iptables -A PINDOU_IN -i lo -j ACCEPT
iptables -A PINDOU_IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A PINDOU_IN -p tcp --dport 22 -j ACCEPT
iptables -A PINDOU_IN -p icmp -j ACCEPT
iptables -A PINDOU_IN -p udp --sport 67 --dport 68 -j ACCEPT
iptables -A PINDOU_IN -j DROP
iptables -C INPUT -j PINDOU_IN 2>/dev/null || iptables -A INPUT -j PINDOU_IN

ip6tables -N PINDOU_IN 2>/dev/null || ip6tables -F PINDOU_IN
ip6tables -A PINDOU_IN -i lo -j ACCEPT
ip6tables -A PINDOU_IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
ip6tables -A PINDOU_IN -p ipv6-icmp -j ACCEPT
ip6tables -A PINDOU_IN -p udp --sport 547 --dport 546 -j ACCEPT
ip6tables -A PINDOU_IN -p tcp --dport 22 -j ACCEPT
ip6tables -A PINDOU_IN -j DROP
ip6tables -C INPUT -j PINDOU_IN 2>/dev/null || ip6tables -A INPUT -j PINDOU_IN
