# Data systems operating notes

## Transactions

Snapshot isolation gives each transaction a consistent snapshot. It can still
permit write skew when concurrent transactions update different rows after
reading the same constraint.

## Recovery

The write-ahead log record must reach durable storage before the corresponding
data page is flushed. This ordering allows recovery to replay committed changes.

## Request handling

When the same idempotency key is retried with the same payload, the service
returns the previously recorded outcome instead of applying the operation twice.

## Objectives

The recovery point objective limits acceptable data loss measured in time. The
recovery time objective limits how long service restoration may take.
