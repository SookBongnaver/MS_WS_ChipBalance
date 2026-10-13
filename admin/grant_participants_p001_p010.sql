-- 참가자 10명 (p001~p010) Unity Catalog 준비 + 권한 부여
-- admin/README.md "1. Unity Catalog와 Serverless" 절 기준

CREATE CATALOG IF NOT EXISTS lab_factory_p001;
CREATE SCHEMA IF NOT EXISTS lab_factory_p001.chipbalance_p001;
CREATE VOLUME IF NOT EXISTS lab_factory_p001.chipbalance_p001.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p001 TO `p001@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p001.chipbalance_p001 TO `p001@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p001.chipbalance_p001.raw TO `p001@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p002;
CREATE SCHEMA IF NOT EXISTS lab_factory_p002.chipbalance_p002;
CREATE VOLUME IF NOT EXISTS lab_factory_p002.chipbalance_p002.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p002 TO `p002@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p002.chipbalance_p002 TO `p002@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p002.chipbalance_p002.raw TO `p002@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p003;
CREATE SCHEMA IF NOT EXISTS lab_factory_p003.chipbalance_p003;
CREATE VOLUME IF NOT EXISTS lab_factory_p003.chipbalance_p003.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p003 TO `p003@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p003.chipbalance_p003 TO `p003@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p003.chipbalance_p003.raw TO `p003@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p004;
CREATE SCHEMA IF NOT EXISTS lab_factory_p004.chipbalance_p004;
CREATE VOLUME IF NOT EXISTS lab_factory_p004.chipbalance_p004.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p004 TO `p004@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p004.chipbalance_p004 TO `p004@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p004.chipbalance_p004.raw TO `p004@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p005;
CREATE SCHEMA IF NOT EXISTS lab_factory_p005.chipbalance_p005;
CREATE VOLUME IF NOT EXISTS lab_factory_p005.chipbalance_p005.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p005 TO `p005@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p005.chipbalance_p005 TO `p005@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p005.chipbalance_p005.raw TO `p005@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p006;
CREATE SCHEMA IF NOT EXISTS lab_factory_p006.chipbalance_p006;
CREATE VOLUME IF NOT EXISTS lab_factory_p006.chipbalance_p006.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p006 TO `p006@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p006.chipbalance_p006 TO `p006@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p006.chipbalance_p006.raw TO `p006@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p007;
CREATE SCHEMA IF NOT EXISTS lab_factory_p007.chipbalance_p007;
CREATE VOLUME IF NOT EXISTS lab_factory_p007.chipbalance_p007.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p007 TO `p007@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p007.chipbalance_p007 TO `p007@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p007.chipbalance_p007.raw TO `p007@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p008;
CREATE SCHEMA IF NOT EXISTS lab_factory_p008.chipbalance_p008;
CREATE VOLUME IF NOT EXISTS lab_factory_p008.chipbalance_p008.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p008 TO `p008@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p008.chipbalance_p008 TO `p008@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p008.chipbalance_p008.raw TO `p008@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p009;
CREATE SCHEMA IF NOT EXISTS lab_factory_p009.chipbalance_p009;
CREATE VOLUME IF NOT EXISTS lab_factory_p009.chipbalance_p009.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p009 TO `p009@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p009.chipbalance_p009 TO `p009@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p009.chipbalance_p009.raw TO `p009@contoso.com`;

CREATE CATALOG IF NOT EXISTS lab_factory_p010;
CREATE SCHEMA IF NOT EXISTS lab_factory_p010.chipbalance_p010;
CREATE VOLUME IF NOT EXISTS lab_factory_p010.chipbalance_p010.raw;
GRANT USE CATALOG ON CATALOG lab_factory_p010 TO `p010@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p010.chipbalance_p010 TO `p010@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p010.chipbalance_p010.raw TO `p010@contoso.com`;

